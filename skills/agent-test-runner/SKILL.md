---
name: agent-test-runner
description: Activate when user invokes @test-runner or requests test execution. Use when user says "测试", "test", "运行测试", "run test". Automatically discovers tests, runs test suites, analyzes results, and generates comprehensive test reports including coverage and performance metrics.
---

# Agent Test Runner

This skill activates the Test Runner Agent to automatically run tests, analyze results, and generate test reports.

## When to Activate

- User invokes `@test-runner`
- User requests test execution
- Before code merge
- After significant changes
- Continuous integration triggers
- Coverage analysis needed
- Performance testing required

## Core Functions

### 1. Test Discovery

Automatically scan for test files:

```bash
# Find LPC unit tests
find . -name "test_*.c" -o -name "*_test.c"

# Find Python tests
find . -name "test_*.py" -o -name "*_test.py"

# Find pytest tests
pytest --collect-only

# Find JavaScript tests
find . -name "*.test.js" -o -name "*.spec.js"
```

**Supported Test Types:**
| Type | Pattern | Framework |
|------|---------|-----------|
| LPC Unit | `test_*.c` | Custom |
| Python Unit | `test_*.py` | pytest/unittest |
| Python Integration | `*_test.py` | pytest |
| JavaScript | `*.test.js` | Jest/Mocha |
| Go | `*_test.go` | testing |
| Rust | `*_test.rs` | cargo test |

### 2. Test Execution

Run tests with appropriate commands:

```bash
# LPC tests
cd legacy-game && ./run_tests.sh

# Python tests
pytest modules/test/
pytest -v  # verbose
pytest -x  # stop on first failure

# Coverage tests
pytest --cov=modules
pytest --cov=modules --cov-report=html
pytest --cov=modules --cov-fail-under=80

# Parallel tests
pytest -n auto

# Specific test file
pytest modules/combat/test_damage.py

# Specific test
pytest modules/combat/test_damage.py::test_critical_hit
```

### 3. Result Analysis

Parse and analyze test output:

**Metrics Extracted:**
- Total tests count
- Pass/fail/skip statistics
- Error details
- Performance metrics
- Coverage percentages

**Failure Analysis:**
```markdown
### 失败分析

#### 1. modules/combat/test_damage.c::test_critical_hit
- **类型**: 断言失败
- **预期**: 200
- **实际**: 195
- **位置**: damage.c:120
- **可能原因**: 
  - 暴击倍率计算错误
  - 伤害加成未生效
- **建议修复**: 检查 critical_multiplier 变量

#### 2. modules/chat/test_channel.c::test_private_message
- **类型**: 超时
- **超时时间**: 5s
- **实际时间**: 8s
- **可能原因**:
  - 网络延迟
  - 消息队列阻塞
- **建议修复**: 增加超时时间或优化异步处理
```

### 4. Test Report Generation

Output structured test report:

```markdown
## 🧪 测试报告

### 执行信息
- **执行时间**: 2024-02-07 15:45:30
- **测试运行器**: pytest 7.4.0
- **总耗时**: 45.2s

### 测试统计
| 指标 | 数量 | 百分比 |
|------|------|--------|
| 总测试数 | 150 | 100% |
| 通过 | 145 | 96.7% |
| 失败 | 3 | 2.0% |
| 跳过 | 2 | 1.3% |
| 错误 | 0 | 0.0% |

### 失败测试详情
#### 1. modules/combat/test_damage.c::test_critical_hit
```
AssertionError: expected 200, got 195
File: damage.c:120
Function: calculate_damage()
```

#### 2. modules/chat/test_channel.c::test_private_message
```
TimeoutError: Test exceeded 5s timeout
Actual time: 8.2s
```

#### 3. modules/user/test_auth.c::test_login_invalid
```
AssertionError: Expected 401, got 200
Invalid credentials should reject login
```

### 覆盖率报告
| 类型 | 覆盖率 | 状态 |
|------|--------|------|
| 行覆盖率 | 85.3% | 🟢 Good |
| 分支覆盖率 | 78.9% | 🟡 Fair |
| 函数覆盖率 | 92.1% | 🟢 Good |

### 模块覆盖率
| 模块 | 行覆盖 | 分支覆盖 | 状态 |
|------|--------|----------|------|
| combat | 92% | 88% | 🟢 |
| chat | 87% | 82% | 🟢 |
| user | 78% | 71% | 🟡 |
| economy | 65% | 58% | 🟠 |

### 性能指标
- **平均执行时间**: 2.3s
- **最慢测试**: test_large_combat (8.5s)
- **内存峰值**: 256MB
- **CPU使用率**: 45%

### 趋势对比
| 指标 | 本次 | 上次 | 变化 |
|------|------|------|------|
| 通过率 | 96.7% | 94.2% | ⬆️ +2.5% |
| 覆盖率 | 85.3% | 83.1% | ⬆️ +2.2% |
| 执行时间 | 45.2s | 52.1s | ⬇️ -13.2% |

### 建议
1. **立即修复**: 3个失败测试影响核心功能
2. **提升覆盖**: economy模块覆盖率需提升
3. **性能优化**: test_large_combat 耗时过长
```

## Usage Examples

### Example 1: Run All Tests
```
User: @test-runner 运行所有测试

AI: [激活 test-runner 代理]

🧪 开始运行测试...

📂 发现测试:
- LPC测试: 120个
- Python测试: 30个
- 集成测试: 15个

🔄 执行测试...
✅ LPC测试: 115/120 通过
✅ Python测试: 30/30 通过
✅ 集成测试: 15/15 通过

[输出完整测试报告]
```

### Example 2: Run Specific Module Tests
```
User: @test-runner 测试combat模块

AI: [激活 test-runner 代理]

🧪 运行combat模块测试...

📂 发现5个测试文件:
- test_damage.c
- test_fight.c
- test_skill.c
- test_ai.c
- test_combat_utils.c

[运行测试并输出模块报告]
```

### Example 3: Run with Coverage
```
User: @test-runner 运行测试并生成覆盖率报告

AI: 
🧪 运行测试 + 覆盖率分析...

📊 覆盖率结果:
- 行覆盖率: 85.3%
- 分支覆盖率: 78.9%
- 函数覆盖率: 92.1%

📁 报告已生成:
- HTML: coverage/index.html
- XML: coverage/coverage.xml
```

### Example 4: Analyze Failures
```
User: @test-runner 分析失败原因

AI: 
🔍 分析测试失败...

发现3个失败测试:

1. test_damage.c::test_critical_hit
   原因: 暴击伤害计算错误
   建议: 检查 critical_multiplier 值

2. test_channel.c::test_private_message
   原因: 异步消息超时
   建议: 增加超时配置

3. test_auth.c::test_login_invalid
   原因: 错误处理逻辑变更
   建议: 更新测试预期值
```

## Test Types

### Unit Tests
- Test individual functions
- Mock external dependencies
- Fast execution
- High isolation

### Integration Tests
- Test module interactions
- Real environment
- Slower execution
- Broader coverage

### Performance Tests
- Response time measurement
- Memory usage tracking
- Concurrency testing
- Load testing

### Security Tests
- SQL injection detection
- Command injection checks
- Authentication validation
- Authorization testing

## Advanced Features

### Parallel Execution
```bash
# Run tests in parallel
pytest -n auto
pytest -n 4  # 4 workers
```

### Failure Retry
```bash
# Retry failed tests
pytest --reruns 3
pytest --reruns 3 --reruns-delay 1
```

### Coverage Thresholds
```bash
# Fail if coverage below threshold
pytest --cov-fail-under=80
pytest --cov-fail-under=90
```

### Selective Testing
```bash
# Run only changed tests
pytest --testmon

# Run failed tests only
pytest --lf

# Run new tests only
pytest --nf
```

## Output Formats

Support multiple report formats:

| Format | Extension | Use Case |
|--------|-----------|----------|
| Markdown | .md | Human readable |
| HTML | .html | Visual report |
| JSON | .json | Machine parsing |
| JUnit XML | .xml | CI/CD integration |
| Cobertura | .xml | Coverage tools |

## Integration Points

This agent may invoke:
- `Skill(agent-code-reviewer)` - Review test code quality
- `Skill(security-review)` - Security test validation
- `Skill(agent-project-manager)` - Update test-related tasks

## Best Practices

1. **Save work** before running tests
2. **Run fast tests first** for quick feedback
3. **Isolate test environments** to prevent conflicts
4. **Clean up resources** after test completion
5. **Document slow tests** with clear comments
6. **Mock external services** for unit tests

## Notes

- Test discovery is automatic and recursive
- Supports test markers and categorization
- Historical trend tracking available
- Performance regression detection
- CI/CD pipeline integration ready
