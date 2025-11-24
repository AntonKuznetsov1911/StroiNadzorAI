"""
Payment Service - Интеграция с платежными системами
Поддержка YooKassa (ЮKassa) для российских пользователей
"""

import logging
import hashlib
import hmac
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

import httpx
from sqlalchemy.orm import Session

from config.settings import settings
from src.database.models import User, UserRole

logger = logging.getLogger(__name__)


class PaymentStatus(str, Enum):
    """Статусы платежа"""
    PENDING = "pending"  # Ожидает оплаты
    PROCESSING = "processing"  # В обработке
    SUCCEEDED = "succeeded"  # Успешно
    CANCELED = "canceled"  # Отменен
    FAILED = "failed"  # Не удалось


class SubscriptionPlan(str, Enum):
    """Планы подписки"""
    FREE = "free"
    PREMIUM_MONTHLY = "premium_monthly"
    PREMIUM_YEARLY = "premium_yearly"


class PaymentService:
    """
    Сервис для работы с платежами
    Интеграция с YooKassa (ЮKassa)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # YooKassa credentials
        self.shop_id = getattr(settings, 'YOOKASSA_SHOP_ID', None)
        self.secret_key = getattr(settings, 'YOOKASSA_SECRET_KEY', None)
        self.api_url = "https://api.yookassa.ru/v3"

        # Цены (в рублях)
        self.prices = {
            SubscriptionPlan.PREMIUM_MONTHLY: 2990,  # 2990₽/месяц
            SubscriptionPlan.PREMIUM_YEARLY: 29900,  # 29900₽/год (скидка ~17%)
        }

        logger.info("PaymentService initialized")

    async def create_payment(
        self,
        user: User,
        plan: SubscriptionPlan,
        return_url: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создать платеж в YooKassa

        Args:
            user: Пользователь
            plan: План подписки
            return_url: URL для возврата после оплаты
            description: Описание платежа

        Returns:
            Dict с данными платежа (включая confirmation_url)
        """
        if plan == SubscriptionPlan.FREE:
            raise ValueError("Cannot create payment for FREE plan")

        amount = self.prices.get(plan)
        if not amount:
            raise ValueError(f"Unknown plan: {plan}")

        if not description:
            description = f"StroiNadzorAI - {plan.value}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/payments",
                    auth=(self.shop_id, self.secret_key),
                    json={
                        "amount": {
                            "value": f"{amount}.00",
                            "currency": "RUB"
                        },
                        "capture": True,
                        "confirmation": {
                            "type": "redirect",
                            "return_url": return_url
                        },
                        "description": description,
                        "metadata": {
                            "user_id": user.id,
                            "telegram_id": user.telegram_id,
                            "plan": plan.value
                        }
                    },
                    headers={
                        "Idempotence-Key": self._generate_idempotence_key(user.id, plan)
                    }
                )

                response.raise_for_status()
                payment_data = response.json()

                logger.info(f"Payment created for user {user.id}: {payment_data['id']}")

                return {
                    "payment_id": payment_data["id"],
                    "status": payment_data["status"],
                    "confirmation_url": payment_data["confirmation"]["confirmation_url"],
                    "amount": amount,
                    "currency": "RUB",
                    "description": description
                }

        except httpx.HTTPError as e:
            logger.error(f"Error creating payment: {e}", exc_info=True)
            raise

    async def check_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Проверить статус платежа

        Args:
            payment_id: ID платежа в YooKassa

        Returns:
            Dict с данными платежа
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/payments/{payment_id}",
                    auth=(self.shop_id, self.secret_key)
                )

                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error checking payment status: {e}", exc_info=True)
            raise

    async def handle_webhook(
        self,
        db: Session,
        webhook_data: Dict[str, Any]
    ) -> bool:
        """
        Обработать webhook от YooKassa

        Args:
            db: Database session
            webhook_data: Данные webhook

        Returns:
            bool: Успешность обработки
        """
        try:
            event = webhook_data.get("event")
            payment = webhook_data.get("object")

            if not payment:
                logger.error("No payment data in webhook")
                return False

            payment_id = payment.get("id")
            status = payment.get("status")
            metadata = payment.get("metadata", {})

            logger.info(f"Webhook received: {event}, payment {payment_id}, status {status}")

            # Обрабатываем только успешные платежи
            if event == "payment.succeeded" and status == "succeeded":
                user_id = metadata.get("user_id")
                plan = metadata.get("plan")

                if not user_id or not plan:
                    logger.error(f"Missing metadata in payment {payment_id}")
                    return False

                # Получаем пользователя
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.error(f"User {user_id} not found")
                    return False

                # Активируем Premium
                self.activate_premium(db, user, plan)

                logger.info(f"Premium activated for user {user_id}, plan {plan}")
                return True

            return True

        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            return False

    def activate_premium(
        self,
        db: Session,
        user: User,
        plan: str
    ):
        """
        Активировать Premium подписку

        Args:
            db: Database session
            user: Пользователь
            plan: План подписки
        """
        # Обновляем роль
        user.role = UserRole.PREMIUM

        # Устанавливаем дату окончания подписки
        if plan == SubscriptionPlan.PREMIUM_MONTHLY.value:
            user.premium_until = datetime.utcnow() + timedelta(days=30)
        elif plan == SubscriptionPlan.PREMIUM_YEARLY.value:
            user.premium_until = datetime.utcnow() + timedelta(days=365)

        db.commit()
        logger.info(f"Premium activated for user {user.id} until {user.premium_until}")

    def check_premium_expiration(self, user: User) -> bool:
        """
        Проверить истекла ли Premium подписка

        Args:
            user: Пользователь

        Returns:
            bool: True если подписка активна
        """
        if user.role != UserRole.PREMIUM:
            return False

        if not user.premium_until:
            return False

        if user.premium_until < datetime.utcnow():
            return False

        return True

    def deactivate_expired_premium(self, db: Session, user: User):
        """
        Деактивировать истекшую Premium подписку

        Args:
            db: Database session
            user: Пользователь
        """
        if not self.check_premium_expiration(user):
            user.role = UserRole.USER
            user.premium_until = None
            db.commit()
            logger.info(f"Premium deactivated for user {user.id}")

    def verify_webhook_signature(
        self,
        webhook_data: str,
        signature: str
    ) -> bool:
        """
        Проверить подпись webhook от YooKassa

        Args:
            webhook_data: JSON данные webhook
            signature: Подпись из заголовка

        Returns:
            bool: Валидность подписи
        """
        try:
            expected_signature = hmac.new(
                self.secret_key.encode(),
                webhook_data.encode(),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False

    def _generate_idempotence_key(self, user_id: int, plan: SubscriptionPlan) -> str:
        """
        Генерировать ключ идемпотентности для платежа

        Args:
            user_id: ID пользователя
            plan: План подписки

        Returns:
            str: Ключ идемпотентности
        """
        timestamp = int(datetime.utcnow().timestamp())
        data = f"{user_id}:{plan.value}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()


# Singleton instance
_payment_service_instance: Optional[PaymentService] = None


def get_payment_service() -> PaymentService:
    """Получить singleton instance PaymentService"""
    global _payment_service_instance
    if _payment_service_instance is None:
        _payment_service_instance = PaymentService()
    return _payment_service_instance
