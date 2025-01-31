import yaml
from pathlib import Path

def load_yaml(file_path):
    """加载 YAML 文件并返回字典"""
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def merge_yaml(base_data, child_data):
    """
    递归合并 YAML 数据，支持多层继承。
    :param base_data: 包含基础定义的字典。
    :param child_data: 包含子定义的字典。
    :return: 合并后的字典。
    """
    merged_data = {}

    for key, value in child_data.items():
        if isinstance(value, dict) and 'base' in value:
            # 如果存在 base 属性，则进行继承
            base_key = value.pop('base')  # 删除 base 键
            if base_key in base_data:
                # 递归合并 base 数据
                base_value = merge_yaml(base_data, {base_key: base_data[base_key]})
                merged_data[key] = {**base_value[base_key], **value}
            else:
                raise ValueError(f"Base key '{base_key}' not found in base data.")
        else:
            # 否则直接复制
            merged_data[key] = value

    return merged_data

def main():
    # 文件路径
    base_file = Path('base.yaml')
    middle_file = Path('middle.yaml')
    child_file = Path('child.yaml')

    # 加载 YAML 文件
    base_data = load_yaml(base_file)
    middle_data = load_yaml(middle_file)
    child_data = load_yaml(child_file)

    # 合并所有数据
    all_data = {**base_data, **middle_data, **child_data}

    # 合并 YAML 数据
    merged_data = merge_yaml(all_data, child_data)

    # 输出合并后的 YAML
    print(yaml.dump(merged_data))

if __name__ == '__main__':
    main()