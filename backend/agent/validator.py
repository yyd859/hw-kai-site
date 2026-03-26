def validate_output(output: dict) -> dict:
    """检查输出合法性，添加 validation 字段"""
    warnings = []
    errors = []
    
    if "{{" in output.get("code", ""):
        errors.append("代码模板中存在未填充的占位符")
    
    if not output.get("bom"):
        errors.append("BOM 为空")
    
    if not output.get("wiring"):
        warnings.append("接线表为空")
    
    if output.get("bom_total_cny", 0) > 500:
        warnings.append("方案总价较高（超过 ¥500），请确认")
    
    output["validation"] = {
        "passed": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
    }
    
    return output
