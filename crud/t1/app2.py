# app.py
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./Chinook.db'  # 替换为你的数据库URI
db = SQLAlchemy(app)

def get_tables():
    # 这个查询适用于SQLite，其他数据库可能需要不同的查询
    query = text("SELECT name FROM sqlite_master WHERE type='table';")
    result = db.session.execute(query)
    return [row[0] for row in result if row[0] != 'sqlite_sequence']

def get_columns(table_name):
    # 这个查询适用于SQLite，其他数据库可能需要不同的查询
    query = text(f"PRAGMA table_info('{table_name}');")
    result = db.session.execute(query)
    return [{'name': row.name, 'type': row.type} for row in result]

@app.route('/')
def index():
    tables = get_tables()
    return render_template('index.html', tables=tables)

@app.route('/list/<table_name>')
def list_items(table_name):
    if table_name not in get_tables():
        return "Table not found", 404
    
    columns = get_columns(table_name)
    query = text(f"SELECT * FROM {table_name}")
    result = db.session.execute(query)
    items = [dict(row) for row in result]
    
    return render_template('list.html', items=items, table_name=table_name, columns=columns)

@app.route('/create/<table_name>', methods=['GET', 'POST'])
def create_item(table_name):
    if table_name not in get_tables():
        return "Table not found", 404
    
    columns = get_columns(table_name)
    
    if request.method == 'POST':
        column_names = [col['name'] for col in columns if col['name'] != 'id']
        values = [request.form.get(col) for col in column_names]
        query = text(f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({', '.join(['?' for _ in values])})")
        db.session.execute(query, values)
        db.session.commit()
        
        # Fetch the last inserted item
        last_id = db.session.execute(text("SELECT last_insert_rowid() as last_id")).fetchone()['last_id']
        item = db.session.execute(text(f"SELECT * FROM {table_name} WHERE id = ?"), [last_id]).fetchone()
        return render_template('item_row.html', item=dict(item), table_name=table_name, columns=columns)
    
    return render_template('create.html', table_name=table_name, columns=columns)

@app.route('/update/<table_name>/<int:id>', methods=['GET', 'POST'])
def update_item(table_name, id):
    if table_name not in get_tables():
        return "Table not found", 404
    
    columns = get_columns(table_name)
    query = text(f"SELECT * FROM {table_name} WHERE id = ?")
    item = db.session.execute(query, [id]).fetchone()
    
    if not item:
        return "Item not found", 404
    
    if request.method == 'POST':
        update_cols = []
        values = []
        for col in columns:
            if col['name'] != 'id':
                update_cols.append(f"{col['name']} = ?")
                values.append(request.form.get(col['name']))
        values.append(id)
        
        query = text(f"UPDATE {table_name} SET {', '.join(update_cols)} WHERE id = ?")
        db.session.execute(query, values)
        db.session.commit()
        
        # Fetch the updated item
        item = db.session.execute(text(f"SELECT * FROM {table_name} WHERE id = ?"), [id]).fetchone()
        return render_template('item_row.html', item=dict(item), table_name=table_name, columns=columns)
    
    return render_template('update.html', item=dict(item), table_name=table_name, columns=columns)

@app.route('/delete/<table_name>/<int:id>', methods=['DELETE'])
def delete_item(table_name, id):
    if table_name not in get_tables():
        return "Table not found", 404
    
    query = text(f"DELETE FROM {table_name} WHERE id = ?")
    db.session.execute(query, [id])
    db.session.commit()
    return "", 204

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')