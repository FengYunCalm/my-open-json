---
name: code-locator
description: Quickly locate code in projects by module name, function name, or keywords. Use when searching for code implementation, finding functions, or user asks "where is", "locate", "定位代码", "查找", "代码在哪".
---

# Code Locator Skill

This skill quickly locates code implementations across the project using various search strategies including module names, function names, and keywords.

## When to Activate

- User asks "where is X implemented?"
- User says "/locate", "定位代码", or "查找功能"
- Need to find specific code quickly
- Exploring unfamiliar codebase

## Search Methods

### 1. Search by Module Name

Find all files related to a specific module:
```bash
/locate combat
```

**Searches for:**
- `modules/combat/` directory
- Files with "combat" in name
- References to combat module
- Related test files

### 2. Search by Function Name

Locate a specific function definition:
```bash
/locate create_party
```

**Searches for:**
- Function definition
- Function declarations
- Function calls
- Related documentation

### 3. Search by Keyword

Find code by feature or concept:
```bash
/locate channel
```

**Searches for:**
- Files containing keyword
- Variable names
- Comments mentioning keyword
- Configuration entries

### 4. Search by File Pattern

Use wildcards for flexible matching:
```bash
/locate *d.c        # Find daemon files
/locate user_*.c    # Find user-related files
/locate *.config.js # Find config files
```

## Search Strategies

### LPC/MUD Projects

```
Search locations:
├── modules/          # Module implementations
├── daemons/          # Daemon processes
├── cmds/             # Command implementations
├── inherit/          # Base classes
├── system/           # System files
└── config/           # Configuration
```

### Web Projects

```
Search locations:
├── src/
│   ├── components/   # UI components
│   ├── views/        # Page components
│   ├── api/          # API definitions
│   ├── utils/        # Utilities
│   └── stores/       # State management
├── public/           # Static assets
└── config/           # Configuration
```

### Mobile Projects

```
Search locations:
├── pages/            # Page components
├── components/       # Reusable components
├── utils/            # Utilities
├── services/         # API services
└── static/           # Static resources
```

## Execution Workflow

### 1. Analyze Query
Parse the search term to determine:
- Is it a module name?
- Is it a function name?
- Is it a file pattern?
- Is it a keyword?

### 2. Execute Search
Run appropriate search commands:
```bash
# File name search
find . -name "*${term}*" -type f

# Content search
grep -r "${term}" --include="*.c" --include="*.h"

# Function definition search
grep -r "^.*${term}\s*(" --include="*.c"

# Module directory search
ls -la modules/${term}/ 2>/dev/null
```

### 3. Process Results
Filter and organize findings:
- Remove duplicates
- Sort by relevance
- Identify main files
- Find related files

### 4. Generate Report

## Output Format

```
📍 Code Location Results: "combat"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 Module: combat

📁 Core Files:
   modules/combat/combat.c      (Main combat logic)
   modules/combat/damage.c      (Damage calculation)
   modules/combat/skill.c       (Skill system)
   modules/combat/battle.c      (Battle management)

📁 Header Files:
   include/combat.h             (Public interface)
   modules/combat/combat.h      (Internal definitions)

📁 Related Files:
   modules/npc/npc_combat.c     (NPC combat behavior)
   cmds/player/fight.c          (Player fight command)
   daemons/combat_d.c           (Combat daemon)

📁 Reference Implementations:
   legacy-game/core/code/feature/combat/fight.c
   legacy-game/core/code/lib/combat.c

📊 Dependencies:
   → Depends on: modules/skill, modules/stat
   → Used by: modules/npc, modules/room

📁 Test Files:
   tests/combat/test_combat.c
   tests/combat/test_damage.c
```

## Search Examples

### Example 1: Module Search
```bash
User: /locate chat

📍 chat Module Location

Core:
- modules/chat/chat.c          (Main chat system)
- modules/chat/channel.c       (Channel management)
- modules/chat/message.c       (Message handling)

Commands:
- cmds/player/chat.c           (Chat command)
- cmds/player/tell.c           (Private message)
- cmds/player/channels.c       (Channel list)

UI:
- web/src/views/chat/          (Chat interface)
- mobile/pages/chat/           (Mobile chat)
```

### Example 2: Function Search
```bash
User: /locate create_party

📍 create_party Function Location

Definition:
- modules/party/party.c:156
  void create_party(object leader, string name)

Declarations:
- include/party.h:45
  void create_party(object, string);

Usages:
- cmds/player/party.c:89
- modules/party/ui.c:234
- tests/party/test_party.c:67
```

### Example 3: Pattern Search
```bash
User: /locate *d.c

📍 Daemon Files

System Daemons:
- daemons/logind.c             (Login daemon)
- daemons/emoted.c             (Emote daemon)
- daemons/channelsd.c          (Channel daemon)

Game Daemons:
- daemons/combat_d.c           (Combat daemon)
- daemons/quest_d.c            (Quest daemon)
- daemons/economy_d.c          (Economy daemon)
```

## Usage Commands

```bash
# Module search
/locate combat
/locate user

# Function search
/locate create_party
/locate calculate_damage

# Keyword search
/locate channel
/locate login

# Pattern search
/locate *d.c
/locate *.vue
/locate user_*

# Natural language
"chat功能在哪"
"定位combat代码"
"查找create_party函数"
"damage计算在哪里"
```

## Advanced Features

### Context Display
Show surrounding code when locating functions:
```
📍 modules/combat/damage.c:45

int calculate_damage(object attacker, object defender, string skill)
{
    int base_damage = attacker->query_str() * 2;
    int defense = defender->query_def();
    int damage = base_damage - defense;
    
    return damage > 0 ? damage : 1;
}
```

### Inheritance Chain
Show class hierarchy for located code:
```
📍 Inheritance Chain: combat.c

object
  └── feature/object
        └── living/living
              └── combat/combat
                    └── combat/advanced_combat
```

### Dependency Graph
Visualize module dependencies:
```
📊 Dependencies: combat

↑ Used By:
  - modules/npc
  - modules/room
  - cmds/player/fight

↓ Depends On:
  - modules/skill
  - modules/stat
  - daemons/combat_d
```

## Tips for Effective Searches

1. **Use specific names** - "create_party" vs "party"
2. **Try different terms** - Module names vs function names
3. **Check multiple locations** - Core vs commands vs UI
4. **Look at tests** - Test files show usage examples
5. **Follow dependencies** - Related modules may have what you need

## Troubleshooting

### No Results Found
- Try broader search terms
- Check spelling
- Search in different directories
- Look for synonyms

### Too Many Results
- Use more specific terms
- Add file type filters
- Search in specific directories
- Use function signatures

---

**Remember**: Efficient code location saves development time. Use specific search terms and explore related files to understand the full context.
