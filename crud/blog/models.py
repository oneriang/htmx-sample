from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import text
from config import load_config

Base = declarative_base()

def create_models1():
    config = load_config()
    models = {}
    
    for model_name, model_def in config['models'].items():
        fields = {'__tablename__': model_def['table']}
        
        for field_name, field_def in model_def['fields'].items():
            # 获取字段类型
            col_type = eval(field_def['type'])
            
            # 构建关键字参数
            kwargs = {k: eval(v) if isinstance(v, str) else v 
                     for k, v in field_def.items() 
                     if k != 'type'}
            
            # 特殊处理 server_default
            if 'server_default' in kwargs:
                kwargs['server_default'] = text(kwargs['server_default'])
                
            fields[field_name] = Column(col_type, **kwargs)
        
        models[model_name] = type(model_name, (Base,), fields)
    
def create_models():
    config = load_config()
    models = {}
    
    for model_name, model_def in config['models'].items():
        fields = {
            '__tablename__': model_def['table'],
            'id': Column(Integer, primary_key=True)
        }
        
        for field, definition in model_def['fields'].items():
            if field != 'id':
                fields[field] = eval(f"Column({definition})")
        
        models[model_name] = type(model_name, (Base,), fields)
    
    return models

models = create_models()