---
name: project-init
description: Initialize project context by loading configuration, progress logs, and displaying current project status. Use when starting work on a project or when asked to "initialize project", "椤圭洰鍒濆鍖?.
---

# Project Init Skill

## Local Integration Note

- If the project has no PROGRESS.md, TODO.md, or equivalent tracking files, skip that part instead of fabricating them.


This skill initializes the project context, loads configuration files, and displays the current project status to prepare for development tasks.

## When to Activate

- Starting work on a new project
- User says "椤圭洰鍒濆鍖? or "initialize project"
- Need to understand project structure and current progress
- Beginning a new development session

## Execution Steps

### 1. Read Project Configuration
- Locate and read project configuration files
- Identify project type (MUD, Web, Mobile, etc.)
- Load project-specific settings and rules

### 2. Load Progress Logs
- Read PROGRESS.md or similar progress tracking files
- Load TODO.md or task lists
- Review recent changes and completed work

### 3. Display Project Status
Show comprehensive project information:
```
馃搳 Project Status

馃搧 Project: [Project Name]
馃敡 Type: [Project Type]
馃搱 Current Phase: [Phase]
鉁?Completed Tasks: [Count]
鈴?Pending Tasks: [Count]
馃幆 Current Focus: [Focus Area]
```

## Project Structure Detection

### MUD Projects
```
Check for:
- modules/ directory
- daemons/ directory
- config.json or similar
- PROGRESS.md
```

### Web Projects
```
Check for:
- package.json
- src/ directory
- README.md
- PROGRESS.md
```

### Mobile Projects
```
Check for:
- App manifest (Android/iOS)
- src/ or app/ directory
- Platform-specific configs
```

## Output Format

```
馃殌 Project Initialization Complete

馃搵 Project Overview:
   - Name: [Name]
   - Type: [Type]
   - Framework: [Framework]

馃搳 Current Progress:
   - Phase: [Current Phase]
   - Tasks Completed: [X/Y]
   - Last Updated: [Date]

馃幆 Ready for Development:
   - Configuration loaded
   - Progress logs synced
   - Project context ready
```

## Verification Checklist

- [ ] Project configuration files located
- [ ] Progress logs loaded successfully
- [ ] Project type identified correctly
- [ ] Current phase determined
- [ ] No critical configuration errors
- [ ] Ready to proceed with development

## Notes

- Always run this skill before starting development tasks
- If configuration is missing, ask user for clarification
- Update progress logs after significant changes
- Maintain accurate project state for better assistance

---

**Remember**: Proper initialization ensures accurate context and better development assistance.


