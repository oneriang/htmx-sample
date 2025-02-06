import yaml

# 嵌入 YAML 数据
base_yaml = """
title: Blog
component_definitions:
  main_layout:
    type: layout
    attributes:
      title: Blog
      url: '/blog'
    children:
      content_main:
        - $ref: content_main
      left_sidebar:
        - type: link
          attributes:
            href: /blog
          config:
            label: Blog
        - type: link
          attributes:
            href: /blog/settings
          config:
            label: Settings
        - type: link
          attributes:
            href: /blog/about
          config:
            label: About
      right_sidebar:
        - type: alert
          attributes:
            class: alert alert-info
            message: This is an informational message.
      
  content_main:
    type: content_main
    attributes:
      id: content_main
    children:
      - type: buttons
        children:
          - type: button
            attributes:
              text: New
              hx-post: /blog/post/form
  
  modal_message:
    id: modal_message
    type: modal_message
    attributes:
      id:
        type: string
        value: modal_message
      title:
        type: string
        value: modal
      content:
        type: string
        value: aaaaa
        
  modal_form:
    id: modal_form
    type: modal_form
    attributes:
      id:
        type: string
        value: modal_form
      title:
        type: string
        value: modal
      content:
        type: string
        value: aaaaa

components:
  - $ref: main_layout
  - $ref: modal_form
  - $ref: modal_message
"""

child_yaml = """
title: Settings
component_definitions:
  main_layout:
    attributes:
      title: Settings
      url: '/blog/settings'
    children:
      content_main:
        - type: alert
        - $ref: form_categorie
        - $ref: container_categories
        - $ref: form_user
        - $ref: container_users
        - $ref: form_tag
        - $ref: container_tags
      
components:
  - $ref: main_layout
"""

def deep_merge(base, child):
    """
    递归合并两个字典，支持深层合并。
    如果字段冲突，优先使用 child 的值。
    """
    if isinstance(base, dict) and isinstance(child, dict):
        merged = base.copy()  # 复制 base 数据
        for key, value in child.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # 如果键存在且值是字典，则递归合并
                merged[key] = deep_merge(merged[key], value)
            else:
                # 否则直接使用 child 的值
                merged[key] = value
        return merged
    else:
        # 如果 base 或 child 不是字典，则直接使用 child 的值
        return child

def resolve_inheritance(data, base_data):
    """
    递归解析继承关系，支持 base 属性。
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
    根据点分隔的路径（如 'parent.form'）获取嵌套字典中的值。
    """
    keys = key_path.split('.')
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current

def main():
    # 加载嵌入的 YAML 数据
    base_data = yaml.safe_load(base_yaml)
    child_data = yaml.safe_load(child_yaml)

    # 合并所有基础数据
    all_base_data = deep_merge(base_data, child_data)

    # 解析继承关系
    resolved_data = resolve_inheritance(child_data, all_base_data)

    # 输出合并后的 YAML
    print(yaml.dump(resolved_data))

if __name__ == '__main__':
    main()