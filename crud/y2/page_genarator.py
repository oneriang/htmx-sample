import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import yaml
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Union, Optional
from jinja2 import Template

app = FastAPI()

# HTML templates as Python strings
BASE_HTML = """
  <!DOCTYPE html>
  <html lang="en" data-theme="light">
  <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{{ page_title }}</title>
      <link href="https://cdn.jsdelivr.net/npm/daisyui@3.1.0/dist/full.css" rel="stylesheet" type="text/css" />
      <script src="https://cdn.tailwindcss.com"></script>
  </head>
  <body>
    {% for component in components %}
        {{ component | safe }}
    {% endfor %}
  </body>
  </html>
"""

HTML_TEMPLATES = {
    'container': '''
        <div class="container mx-auto {{ attributes.class.value }}">
            {% for child in children %}
                {{ child | safe }}
            {% endfor %}
        </div>
    ''',
    'card': '''
        <div class="card w-full {{ attributes.class.value }}">
            <div class="card-body">
                <h2 class="card-title">{{ attributes.title.value }}</h2>
                <p>{{ attributes.content.value }}</p>
                {% for child in children %}
                    {{ child | safe }}
                {% endfor %}
            </div>
        </div>
    ''',
    'grid': '''
        <div class="grid grid-cols-{{ attributes.columns.value }} {{ attributes.class.value }}">
            {% for child in children %}
                <div class="col-span-1">{{ child | safe }}</div>
            {% endfor %}
        </div>
    ''',
    'table': '''
        <div class="overflow-x-auto">
            <table class="table {{ attributes.class.value }}">
                <thead>
                    <tr>
                        {% for header in attributes.headers.value %}
                            <th>{{ header }}</th>
                        {% endfor %}
                    </tr>
                </thead>
                <tbody>
                    {% for row in attributes.rows.value %}
                        <tr>
                            {% for cell in row %}
                                <td>{{ cell }}</td>
                            {% endfor %}
                        </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    ''',
    'form': '''
        <form class="{{ attributes.class.value }}">
            {% for field in attributes.fields.value %}
                <div class="form-control w-full mb-4">
                    <label class="label">
                        <span class="label-text">{{ field.label }}</span>
                    </label>
                    {% if field.type == 'text' or field.type == 'email' or field.type == 'password' or field.type == 'number' or field.type == 'date' %}
                        <input type="{{ field.type }}" name="{{ field.name }}" placeholder="{{ field.placeholder }}" class="input input-bordered w-full" {% if field.required %}required{% endif %}>
                    {% elif field.type == 'textarea' %}
                        <textarea name="{{ field.name }}" placeholder="{{ field.placeholder }}" class="textarea textarea-bordered w-full" {% if field.required %}required{% endif %}></textarea>
                    {% elif field.type == 'select' %}
                        <select name="{{ field.name }}" class="select select-bordered w-full" {% if field.required %}required{% endif %}>
                            {% for option in field.options %}
                                <option value="{{ option.value }}">{{ option.label }}</option>
                            {% endfor %}
                        </select>
                    {% elif field.type == 'checkbox' %}
                        <div class="flex items-center mt-2">
                            <input type="checkbox" name="{{ field.name }}" class="checkbox" {% if field.required %}required{% endif %}>
                            <span class="ml-2">{{ field.checkboxLabel }}</span>
                        </div>
                    {% elif field.type == 'radio' %}
                        <div class="flex flex-col mt-2">
                            {% for option in field.options %}
                                <label class="flex items-center mb-2">
                                    <input type="radio" name="{{ field.name }}" value="{{ option.value }}" class="radio" {% if field.required %}required{% endif %}>
                                    <span class="ml-2">{{ option.label }}</span>
                                </label>
                            {% endfor %}
                        </div>
                    {% elif field.type == 'file' %}
                        <input type="file" name="{{ field.name }}" class="file-input file-input-bordered w-full" {% if field.required %}required{% endif %}>
                    {% endif %}
                    {% if field.helpText %}
                        <label class="label">
                            <span class="label-text-alt text-info">{{ field.helpText }}</span>
                        </label>
                    {% endif %}
                </div>
            {% endfor %}
            <button type="submit" class="btn btn-primary w-full mt-4">{{ attributes.submit_text.value }}</button>
        </form>
    ''',
    'navbar': '''
        <div class="navbar bg-base-100 {{ attributes.class.value }}">
            <div class="flex-1">
                <a class="btn btn-ghost normal-case text-xl">{{ attributes.title.value }}</a>
            </div>
            <div class="flex-none hidden md:block">
                <ul class="menu menu-horizontal px-1">
                    {% for item in attributes.menu_items.value %}
                        <li><a href="{{ item.link }}">{{ item.text }}</a></li>
                    {% endfor %}
                </ul>
            </div>
            <div class="flex-none md:hidden">
                <button class="btn btn-square btn-ghost" data-drawer-target="my-drawer">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-5 h-5 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
                </button>
            </div>
        </div>
    ''',
    'button': '''
        <button class="btn {{ attributes.class.value }}" 
                {% if attributes.modal_target and attributes.modal_target.value %}data-modal-target="{{ attributes.modal_target.value }}"{% endif %}
                {% if attributes.drawer_target and attributes.drawer_target.value %}data-drawer-target="{{ attributes.drawer_target.value }}"{% endif %}>
            {{ attributes.text.value }}
        </button>
    ''',
    'modal': '''
        <dialog id="{{ attributes.id.value }}" class="modal">
            <form method="dialog" class="modal-box">
                <h3 class="font-bold text-lg">{{ attributes.title.value }}</h3>
                <p class="py-4">{{ attributes.content.value }}</p>
                <div class="modal-action">
                    <button class="btn close-modal">Close</button>
                </div>
            </form>
        </dialog>
    ''',
}

# Updated Pydantic models
class ComponentAttribute(BaseModel):
    type: str
    value: Optional[Union[str, int, float, bool, List, Dict]] = None

class Component(BaseModel):
    type: str
    attributes: Dict[str, ComponentAttribute] = Field(default_factory=dict)
    children: List['Component'] = Field(default_factory=list)

class Page(BaseModel):
    title: str
    components: List[Component]


# YAML configuration as a Python string
YAML_CONFIG = """
  title: Responsive Dashboard with Drawers
  components:
    - type: navbar
      attributes:
        title: 
          type: string
          value: My Dashboard
        class:
          type: string
          value: mb-4
        menu_items:
          type: list
          value:
            - {text: Home, link: "#"}
            - {text: About, link: "#about"}
            - {text: Contact, link: "#contact"}
    - type: container
      attributes:
        class:
          type: string
          value: "px-4 py-8"
      children:
        - type: grid
          attributes:
            columns:
              type: string
              value: "1 md:3"
            class:
              type: string
              value: gap-4
          children:
            - type: stat
              attributes:
                title:
                  type: string
                  value: Total Users
                value:
                  type: string
                  value: "25.6K"
                description:
                  type: string
                  value: "21% more than last month"
                icon:
                  type: string
                  value: "<svg>...</svg>"
            - type: stat
              attributes:
                title:
                  type: string
                  value: Page Views
                value:
                  type: string
                  value: "2.6M"
                description:
                  type: string
                  value: "14% more than last week"
                icon:
                  type: string
                  value: "<svg>...</svg>"
            - type: stat
              attributes:
                title:
                  type: string
                  value: New Registrations
                value:
                  type: string
                  value: "+573"
                description:
                  type: string
                  value: "36% more than last month"
                icon:
                  type: string
                  value: "<svg>...</svg>"
        - type: form
          attributes:
            class:
              type: string
              value: mt-4 max-w-md mx-auto
            fields:
              type: list
              value:
                - {name: username, type: text, label: Username, placeholder: Enter your username, required: true}
                - {name: email, type: email, label: Email, placeholder: Enter your email, required: true}
                - {name: password, type: password, label: Password, placeholder: Enter your password, required: true}
                - {name: age, type: number, label: Age, placeholder: Enter your age}
                - {name: birthdate, type: date, label: Birth Date}
                - {name: bio, type: textarea, label: Biography, placeholder: Tell us about yourself}
                - name: country
                  type: select
                  label: Country
                  required: true
                  options:
                    - {value: us, label: United States}
                    - {value: uk, label: United Kingdom}
                    - {value: ca, label: Canada}
                - name: newsletter
                  type: checkbox
                  label: Subscribe to newsletter
                  checkboxLabel: Yes, I want to receive updates
                - name: gender
                  type: radio
                  label: Gender
                  options:
                    - {value: male, label: Male}
                    - {value: female, label: Female}
                    - {value: other, label: Other}
                - name: profile_picture
                  type: file
                  label: Profile Picture
                  helpText: Please upload an image file (JPG, PNG)
            submit_text:
              type: string
              value: Register
"""

def load_page_config() -> Page:
    config = yaml.safe_load(YAML_CONFIG)
    return Page(**config)

def generate_html(component: Component) -> str:
    template = Template(HTML_TEMPLATES.get(component.type, ''))
    rendered_children = [generate_html(child) for child in component.children]
    return template.render(attributes=component.attributes, children=rendered_children)

@app.get("/", response_class=HTMLResponse)
async def render_page(request: Request):
    page_config = load_page_config()
    rendered_components = [generate_html(component) for component in page_config.components]
    
    template = Template(BASE_HTML)
    return template.render(
        page_title=page_config.title,
        components=rendered_components
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=2,
        log_level="debug",
        access_log=False,
        reload_dirs=["./"]
    )
