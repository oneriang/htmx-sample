# app.py
from flask import Flask, render_template, request, jsonify
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)

# 创建数据库引擎
engine = create_engine('sqlite:///./Chinook.db')

# 创建会话工厂
Session = sessionmaker(bind=engine)

def get_tables():
    inspector = inspect(engine)
    return inspector.get_table_names()

def get_columns(table_name):
    inspector = inspect(engine)
    return [{"name": column['name'], "type": str(column['type'])} for column in inspector.get_columns(table_name)]

@app.route('/')
def index():
    tables = get_tables()
    return render_template('index.html', tables=tables)

@app.route('/list/<table_name>')
def list_items(table_name):
    if table_name not in get_tables():
        return "Table not found", 404
    
    columns = get_columns(table_name)
    print(columns)
    with Session() as session:
        # query = text(f"SELECT * FROM {table_name}")
        # result = session.execute(query)
        # items = [dict(row) for row in result]
        query = text(f"SELECT * FROM {table_name}")
        result = session.execute(query)
        items = [row._asdict() for row in result]
    print(items)
    return render_template('list.html', items=items, table_name=table_name, columns=columns)

@app.route('/create/<table_name>', methods=['GET', 'POST'])
def create_item(table_name):
    if table_name not in get_tables():
        return "Table not found", 404
    
    columns = get_columns(table_name)
    
    if request.method == 'POST':
        with Session() as session:
            column_names = [col['name'] for col in columns if col['name'].lower() != 'id']
            values = [request.form.get(col) for col in column_names]
            query = text(f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({', '.join(['?' for _ in values])})")
            session.execute(query, values)
            session.commit()
            
            # Fetch the last inserted item
            last_id_query = text("SELECT last_insert_rowid() as last_id")
            last_id = session.execute(last_id_query).fetchone()['last_id']
            item_query = text(f"SELECT * FROM {table_name} WHERE id = :id")
            item = session.execute(item_query, {'id': last_id}).fetchone()
        
        return render_template('item_row.html', item=dict(item), table_name=table_name, columns=columns)
    
    return render_template('create.html', table_name=table_name, columns=columns)

@app.route('/update/<table_name>/<int:id>', methods=['GET', 'POST'])
def update_item(table_name, id):
    if table_name not in get_tables():
        return "Table not found", 404
    
    columns = get_columns(table_name)
    
    with Session() as session:
        query = text(f"SELECT * FROM {table_name} WHERE id = :id")
        item = session.execute(query, {'id': id}).fetchone()
    
    if not item:
        return "Item not found", 404
    
    if request.method == 'POST':
        with Session() as session:
            update_cols = []
            values = {}
            for col in columns:
                if col['name'].lower() != 'id':
                    update_cols.append(f"{col['name']} = :{col['name']}")
                    values[col['name']] = request.form.get(col['name'])
            values['id'] = id
            
            query = text(f"UPDATE {table_name} SET {', '.join(update_cols)} WHERE id = :id")
            session.execute(query, values)
            session.commit()
            
            # Fetch the updated item
            item_query = text(f"SELECT * FROM {table_name} WHERE id = :id")
            item = session.execute(item_query, {'id': id}).fetchone()
        
        return render_template('item_row.html', item=dict(item), table_name=table_name, columns=columns)
    
    return render_template('update.html', item=dict(item), table_name=table_name, columns=columns)

@app.route('/delete/<table_name>/<int:id>', methods=['DELETE'])
def delete_item(table_name, id):
    if table_name not in get_tables():
        return "Table not found", 404
    
    with Session() as session:
        query = text(f"DELETE FROM {table_name} WHERE id = :id")
        session.execute(query, {'id': id})
        session.commit()
    
    return "", 204

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')