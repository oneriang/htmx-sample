import yaml

# 嵌入 YAML 数据
base_yaml = """
parent:
    layout:
        type: layout_base_type_1
        config:
            title: Base Layout Title
            mode: base_mode

    form:
        type: form_base_type_1
        config:
            title: Base Form Title
            mode: base_mode
"""

child_yaml = """
parent:
    layout:
        config:
            title: Child Layout Title
        styles:
            font-size: 16px
    form:
        config:
            title: Child Form Title
        fields:
            age: 25
    form1:
        base: parent.form
        config:
            title: Child Form Title
        fields:
            age: 25
"""

def deep_merge(base_data, child_data):
    """
    递归合并字典，支持深层合并。
    """
    if isinstance(child_data, dict) and isinstance(base_data, dict):
        for key, value in child_data.items():
            if key in base_data:
                base_data[key] = deep_merge(base_data[key], value)
            else:
                base_data[key] = value
        return base_data
    else:
        return child_data

def resolve_inheritance(data, base_data):
    """
    递归解析继承关系，支持任意层级的 base 属性。
    """
    if isinstance(data, dict):
        # 如果存在 base 属性，则进行继承
        if 'base' in data:
            base_key = data.pop('base')  # 删除 base 键
            # 递归查找 base 数据
            base_value = get_nested_value(base_data, base_key)
            if base_value is not None:
                # 递归解析 base 数据
                base_value = resolve_inheritance(base_value, base_data)
                # 深层合并 base 数据和当前数据
                data = deep_merge(base_value, data)
            else:
                raise ValueError(f"Base key '{base_key}' not found in base data.")

        # 递归处理所有子属性
        for key, value in data.items():
            data[key] = resolve_inheritance(value, base_data)

    elif isinstance(data, list):
        # 如果是列表，递归处理每个元素
        data = [resolve_inheritance(item, base_data) for item in data]

    return data

def get_nested_value(data, key_path):
    """
    根据点分隔的路径（如 'parent.layout'）获取嵌套字典中的值。
    如果 key_path 不包含点，则直接查找键。
    """
    if '.' in key_path:
        keys = key_path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
    else:
        # 如果 key_path 不包含点，则直接查找键
        return data.get(key_path)

def main():
    # 加载嵌入的 YAML 数据
    base_data = yaml.safe_load(base_yaml)
    child_data = yaml.safe_load(child_yaml)

    # 合并所有基础数据
    all_base_data = {**base_data, **child_data}
    print(all_base_data)

    # 解析继承关系
    resolved_data = resolve_inheritance(child_data, all_base_data)
    print(resolved_data)
    
    # 输出合并后的 YAML
    print(yaml.dump(resolved_data))

if __name__ == '__main__':
    main()