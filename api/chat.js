var SYSTEM_PROMPT = 'Ты — экспертный AI-консультант по строительным нормативам Российской Федерации. Твои знания включают:\n' +
  '- Своды правил (СП), ГОСТ, СНиП, Федеральные законы\n' +
  '- Технологии строительных работ\n' +
  '- Расчёт конструкций и материалов\n' +
  '- Контроль качества и строительный надзор\n' +
  '- Безопасность труда в строительстве\n' +
  '- Проектирование зданий и сооружений\n' +
  '- Сметное дело и ценообразование\n\n' +
  'Правила ответа:\n' +
  '- Отвечай профессионально, но понятно\n' +
  '- Ссылайся на конкретные нормативные документы (СП, ГОСТ, СНиП) где возможно\n' +
  '- Если вопрос не относится к строительству, вежливо направь пользователя к строительной тематике\n' +
  '- Давай практические рекомендации\n' +
  '- Используй структурированные ответы с пунктами где уместно';

var ALLOWED_ORIGINS = [
  'https://antonkuznetsov1911.github.io',
  'http://localhost',
  'http://localhost:3000',
  'http://127.0.0.1'
];

function setCors(res, origin) {
  for (var i = 0; i < ALLOWED_ORIGINS.length; i++) {
    if (origin && origin.startsWith(ALLOWED_ORIGINS[i])) {
      res.setHeader('Access-Control-Allow-Origin', origin);
      break;
    }
  }
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

async function callGemini(message, history) {
  var key = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (!key) throw new Error('No Gemini key');

  var contents = [];
  var start = Math.max(0, history.length - 18);
  for (var i = start; i < history.length; i++) {
    var m = history[i];
    contents.push({
      role: m.role === 'user' ? 'user' : 'model',
      parts: [{ text: m.content }]
    });
  }
  contents.push({ role: 'user', parts: [{ text: message }] });

  var resp = await fetch(
    'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + key,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: contents,
        systemInstruction: { parts: [{ text: SYSTEM_PROMPT }] },
        generationConfig: { temperature: 0.7, maxOutputTokens: 4096 }
      })
    }
  );
  if (!resp.ok) throw new Error('Gemini HTTP ' + resp.status);
  var data = await resp.json();
  return data.candidates[0].content.parts[0].text;
}

async function callGrok(message, history) {
  var key = process.env.XAI_API_KEY;
  if (!key) throw new Error('No xAI key');

  var messages = [{ role: 'system', content: SYSTEM_PROMPT }];
  var start = Math.max(0, history.length - 18);
  for (var i = start; i < history.length; i++) {
    messages.push({ role: history[i].role, content: history[i].content });
  }
  messages.push({ role: 'user', content: message });

  var resp = await fetch('https://api.x.ai/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + key
    },
    body: JSON.stringify({
      model: 'grok-3-fast',
      messages: messages,
      max_tokens: 4096,
      temperature: 0.7
    })
  });
  if (!resp.ok) throw new Error('Grok HTTP ' + resp.status);
  var data = await resp.json();
  return data.choices[0].message.content;
}

async function callClaude(message, history) {
  var key = process.env.ANTHROPIC_API_KEY;
  if (!key) throw new Error('No Anthropic key');

  var messages = [];
  var start = Math.max(0, history.length - 18);
  for (var i = start; i < history.length; i++) {
    messages.push({ role: history[i].role, content: history[i].content });
  }
  messages.push({ role: 'user', content: message });

  var resp = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': key,
      'anthropic-version': '2023-06-01'
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-5-20250929',
      max_tokens: 4096,
      system: SYSTEM_PROMPT,
      messages: messages
    })
  });
  if (!resp.ok) throw new Error('Claude HTTP ' + resp.status);
  var data = await resp.json();
  return data.content[0].text;
}

async function callOpenai(message, history) {
  var key = process.env.OPENAI_API_KEY;
  if (!key) throw new Error('No OpenAI key');

  var messages = [{ role: 'system', content: SYSTEM_PROMPT }];
  var start = Math.max(0, history.length - 18);
  for (var i = start; i < history.length; i++) {
    messages.push({ role: history[i].role, content: history[i].content });
  }
  messages.push({ role: 'user', content: message });

  var resp = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + key
    },
    body: JSON.stringify({
      model: 'gpt-4o-mini',
      messages: messages,
      max_tokens: 4096,
      temperature: 0.7
    })
  });
  if (!resp.ok) throw new Error('OpenAI HTTP ' + resp.status);
  var data = await resp.json();
  return data.choices[0].message.content;
}

var PROVIDERS = [
  ['Gemini', callGemini],
  ['Grok', callGrok],
  ['Claude', callClaude],
  ['OpenAI', callOpenai]
];

module.exports = async function handler(req, res) {
  var origin = req.headers.origin || '';
  setCors(res, origin);

  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }

  if (req.method === 'GET') {
    res.status(200).json({ status: 'ok', service: 'StroiNadzorAI API' });
    return;
  }

  if (req.method !== 'POST') {
    res.status(405).json({ detail: 'Method not allowed' });
    return;
  }

  var body = req.body || {};
  var message = (body.message || '').trim();
  var history = body.history || [];

  if (!message) {
    res.status(400).json({ detail: 'Пустое сообщение' });
    return;
  }

  for (var i = 0; i < PROVIDERS.length; i++) {
    var name = PROVIDERS[i][0];
    var fn = PROVIDERS[i][1];
    try {
      var answer = await fn(message, history);
      if (answer && answer.trim()) {
        res.status(200).json({ answer: answer, provider: name });
        return;
      }
    } catch (e) {
      // fallback to next provider
    }
  }

  res.status(503).json({ detail: 'Все AI-провайдеры недоступны. Попробуйте позже.' });
};
