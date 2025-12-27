# StroiNadzorAI v3.9 - New Features

## New Features Added

### 1. Voice Messages Support
- **Module**: `voice_handler.py`
- **Description**: Speech recognition using OpenAI Whisper API
- **Usage**: Send voice message to the bot
- **Features**:
  - Automatic voice-to-text conversion
  - Russian language support
  - Temporary file management
  - Error handling

### 2. Document Templates
- **Module**: `document_templates.py`
- **Description**: Generate construction documents from templates
- **Usage**: `/templates` command
- **Available Templates**:
  - Foundation acceptance act
  - Contractor complaint
  - Safety plan
  - Hidden works act
- **Output**: DOCX format

### 3. Project Management
- **Module**: `project_manager.py`
- **Description**: Upload and manage project files
- **Usage**: 
  - `/projects` - list projects
  - `/new_project <name>` - create project
  - Send files to add to project
- **Features**:
  - File upload and storage
  - Project metadata
  - File organization
  - Project summaries

## Setup

### Requirements
Add to `.env`:
```
OPENAI_API_KEY=your_openai_api_key_here
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Usage Examples

### Voice Messages
1. Send voice message to bot
2. Bot recognizes speech
3. Bot processes as text query

### Document Generation
1. `/templates`
2. Select template
3. Enter parameters
4. Receive DOCX file

### Project Files
1. `/new_project My Building`
2. Send files with descriptions
3. `/projects` to view

