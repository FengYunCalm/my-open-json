---
name: dev-workflow
description: Execute the 7-step development workflow for feature development. Use when developing new features, implementing requirements, or when user asks to "寮€鍙戝姛鑳?, "dev feature".
---

# Dev Workflow Skill

## Local Integration Note

- Use this only when the user explicitly wants a heavy feature workflow.
- Do not assume every project has progress logs, plan docs, or a dedicated git commit helper.


This skill implements a standardized 7-step development workflow for feature development, ensuring consistent quality and comprehensive implementation.

## When to Activate

- User requests new feature development
- Implementing a new module or functionality
- Starting a development task
- User says "/dev" or "寮€鍙戞柊鍔熻兘"

## The 7-Step Workflow

```
闇€姹傛緞娓?鈫?鎶€鏈璁?鈫?鏁版嵁搴撹璁?鈫?鍚庣寮€鍙?鈫?鍓嶇寮€鍙?鈫?娴嬭瘯楠岃瘉 鈫?鏂囨。鏇存柊
   鈫?        鈫?         鈫?          鈫?         鈫?         鈫?         鈫?
 纭      鏂规       SQL浠ｇ爜      鍥涘眰浠ｇ爜    UI缁勪欢    鍔熻兘娴嬭瘯   鏇存柊鏃ュ織
```

## Step 1: Requirements Clarification

### Actions
- Ask clarifying questions about the feature
- Confirm business rules and constraints
- Define inputs and outputs
- Identify edge cases

### Questions to Ask
- What is the core purpose of this feature?
- Who are the target users?
- What are the acceptance criteria?
- Are there any dependencies on other modules?
- What are the performance requirements?

### Output
- Clear feature description
- Defined acceptance criteria
- Identified constraints and dependencies

## Step 2: Technical Design

### Actions
- Identify database tables needed
- Design API interfaces
- Plan frontend pages/components
- Select appropriate technology solutions

### Checklist
- [ ] Database schema planned
- [ ] API endpoints designed
- [ ] Frontend components outlined
- [ ] Technology choices justified
- [ ] Security considerations addressed

### Output
- Technical design document
- API specification
- Component hierarchy

## Step 3: Database Design

### Actions
- Generate table creation SQL
- Configure data dictionary
- Plan migration scripts
- Insert necessary menu/permission data

### LPC Projects
```sql
-- Example: Creating a new table
CREATE TABLE IF NOT EXISTS feature_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Output
- SQL creation scripts
- Data dictionary entries
- Migration plan

## Step 4: Backend Development

### Actions
- Generate code following 4-layer architecture
- Entity 鈫?BO/VO 鈫?DAO 鈫?Service 鈫?Controller
- Follow project coding standards
- Implement business logic

### 4-Layer Architecture
```
Entity (Data Model)
    鈫?
BO/VO (Business Object / Value Object)
    鈫?
DAO (Data Access Object)
    鈫?
Service (Business Logic)
    鈫?
Controller (API Endpoint)
```

### Output
- Complete backend implementation
- Unit tests
- API documentation

## Step 5: Frontend Development

### Actions
- Generate API client definitions
- Create page components
- Configure routing
- Set up permissions

### Vue Projects
- Create `.vue` components
- Define API calls
- Configure routes
- Add to navigation menu

### Mobile Projects
- Create platform-specific components
- Implement API integration
- Handle responsive design

### Output
- Frontend components
- API integration
- Route configuration

## Step 6: Testing & Validation

### Actions
- Start development services
- Execute functional tests
- Test boundary conditions
- Verify error handling

### Testing Checklist
- [ ] Happy path tested
- [ ] Edge cases covered
- [ ] Error scenarios handled
- [ ] Performance acceptable
- [ ] Security validated

### Output
- Test results
- Bug fixes
- Performance metrics

## Step 7: Documentation Update

### Actions
- Update PROGRESS.md
- Record completed tasks
- Document any pending items
- Commit all changes

### Update Items
- [ ] PROGRESS.md updated
- [ ] TODO.md adjusted
- [ ] Code comments added
- [ ] README updated if needed
- [ ] Git commits made

## Supported Skills

This workflow may invoke:
- `code-locator` - Find relevant existing code
- `code-review` - Review generated code
- `git-commit-helper` - Generate commit messages
- `task-cleanup` - Clean up temporary files

## Usage Examples

```bash
# Basic usage
/dev 寮€鍙戜紭鎯犲埜绠＄悊鍔熻兘

# With specific module
/dev 涓?combat 妯″潡娣诲姞鏆村嚮浼ゅ鍔熻兘

# Complex feature
/dev 瀹炵幇鐜╁缁勯槦绯荤粺锛屽寘鎷垱寤洪槦浼嶃€侀個璇锋垚鍛樸€佽涪鍑烘垚鍛樺姛鑳?
```

## Best Practices

1. **User Confirmation**: Wait for user confirmation at each step
2. **Incremental Progress**: Complete one step before moving to next
3. **Proactive Questions**: Ask when requirements are unclear
4. **Git Safety**: One file per commit following Git best practices
5. **Code Reuse**: Prefer existing components and utilities

## Flowchart

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹? Requirements   鈹傗梽鈹€鈹€ Ask questions, clarify scope
鈹? Clarification  鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
         鈻?
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?  Technical     鈹傗梽鈹€鈹€ Design architecture, APIs
鈹?   Design       鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
         鈻?
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?   Database     鈹傗梽鈹€鈹€ Create tables, migrations
鈹?   Design       鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
         鈻?
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?   Backend      鈹傗梽鈹€鈹€ 4-layer architecture
鈹?  Development   鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
         鈻?
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?   Frontend     鈹傗梽鈹€鈹€ Components, routing
鈹?  Development   鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
         鈻?
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?    Testing     鈹傗梽鈹€鈹€ Functional, boundary tests
鈹?  & Validation  鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
         鈻?
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
鈹?  Documentation 鈹傗梽鈹€鈹€ Update logs, commit
鈹?   & Cleanup    鈹?
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?
```

---

**Remember**: Follow the workflow sequentially. Each step builds upon the previous one. When in doubt, ask the user before proceeding.


