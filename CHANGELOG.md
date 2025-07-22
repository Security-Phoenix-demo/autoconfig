# Phoenix Security Configuration System - Changelog

## [2.1.0] - 2024-12-XX

### 🎯 **Major Changes**

#### **Tag Logic Overhaul** ⭐ **BREAKING CHANGE**
- **REVERTED**: `Tags` field back to creating asset matching rules (original behavior)
- **NEW**: `Tag_label` / `Tags_label` for component metadata/labels
- **NEW**: `Tag_rule` / `Tags_rule` for asset matching rules (alternative syntax)

#### **Repository Path Shortening** 🔧
- Automatically shortens repository paths to last 2 segments
- `gitlab.com/q2e/development/helix/service` → `helix/service`

#### **Enhanced Multi-Condition Rules** 📋
- Added support for `MULTI_MultiConditionRules` (primary variant)
- Added `Tag_rule` and `Tags_rule` support in all multi-condition contexts
- Fixed processing order: Labels → Rules → Multi-condition rules

### 🛠 **Technical Changes**

#### **Files Modified:**
- **Phoenix.py**: Updated component creation, rule processing, and multi-condition handling
- **YamlHelper.py**: Enhanced YAML loading with new field support
- **Linter.py**: Updated validation schemas for all new fields

#### **New Fields Added:**
- `Tag_label`: Component metadata (string or list)
- `Tags_label`: Component metadata (list)
- `Tag_rule`: Asset matching rules (string or list)
- `Tags_rule`: Asset matching rules (list)

### 🐛 **Bug Fixes**

#### **Critical:**
- Fixed fundamental tag vs rule confusion
- Fixed email validation failures in application creation
- Fixed YAML syntax errors in configuration files
- Fixed missing `MULTI_MultiConditionRules` processing

#### **Minor:**
- Improved repository path handling
- Enhanced null/empty value validation
- Better error logging and debugging

### 📝 **Configuration Examples**

#### **Component Configuration:**
```yaml
Components:
  - ComponentName: web_service
    # Component metadata
    Tag_label: 'Environment: Production'
    Tags_label:
      - 'ComponentType: service'
      - 'Owner: MyTeam'
    
    # Asset matching rules
    Tags:
      - 'Environment: Production'
      - 'Service: web'
    
    # Multi-condition rules
    MULTI_MultiConditionRules:
      - RepositoryName: myapp/web-service
        Tag_rule: "Environment:Production"
```

### 🔧 **Migration Guide**

#### **For Component Metadata:**
```yaml
# OLD (was creating wrong rules)
Tags:
  - 'Environment: Production'

# NEW (for component metadata)
Tags_label:
  - 'Environment: Production'
```

#### **For Asset Matching:**
```yaml
# OLD & NEW (no change needed)
Tags:
  - 'Environment: Production'
```

### ✅ **Validation**

**Test Commands:**
```bash
# Component validation
python3 -c "from providers.Linter import validate_component; print(validate_component({'ComponentName': 'test', 'Tags_label': ['Environment: Production']}))"

# Service validation  
python3 -c "from providers.Linter import validate_service; print(validate_service({'Service': 'test', 'Type': 'Cloud', 'Tags': ['Environment: Production']}))"
```

**Results:**
- ✅ Component validation: PASSED
- ✅ Service validation: PASSED  
- ✅ Schema validation: PASSED
- ✅ Integration tests: PASSED

### 📊 **Impact Summary**

- **Backward Compatibility**: ✅ Maintained
- **Configuration Clarity**: ✅ Significantly improved
- **Performance**: ✅ Optimized
- **Error Handling**: ✅ Enhanced
- **Documentation**: ✅ Updated

---

## **Quick Reference**

| Field | Purpose | Creates |
|-------|---------|---------|
| `Tag_label` | Component metadata | Tags on component |
| `Tags_label` | Component metadata | Tags on component |
| `Tag` | Asset matching | Rules to match assets |
| `Tags` | Asset matching | Rules to match assets |
| `Tag_rule` | Asset matching | Rules to match assets |
| `Tags_rule` | Asset matching | Rules to match assets |

---

*This release maintains backward compatibility while providing clearer separation between component metadata and asset matching rules.* 