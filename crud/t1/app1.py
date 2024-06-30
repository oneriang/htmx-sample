# app.py
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./Chinook.db'  # 替换为你的数据库 URI
db = SQLAlchemy(app)

def get_tables():
    print('get_tables')
    print(db.engine)
    inspector = inspect(db.engine)
    print(inspector)
    return inspector.get_table_names()

def get_columns(table_name):
    inspector = inspect(db.engine)
    return [column['name'] for column in inspector.get_columns(table_name)]

@app.route('/')
def index():
    tables = get_tables()
    print(tables)
    return render_template('index.html', tables=tables)

@app.route('/list/<table_name>')
def list_items(table_name):
    if table_name not in get_tables():
        return "Table not found", 404
    
    columns = get_columns(table_name)
    query = text(f"SELECT * FROM {table_name}")
    result = db.session.execute(query)
    items = [dict(zip(columns, row)) for row in result]
    
    return render_template('list.html', items=items, table_name=table_name, columns=columns)

@app.route('/create/<table_name>', methods=['GET', 'POST'])
def create_item(table_name):
    if table_name not in get_tables():
        return "Table not found", 404
    
    columns = get_columns(table_name)
    if request.method == 'POST':
        values = [request.form.get(column) for column in columns if column != 'id']
        columns_str = ', '.join([col for col in columns if col != 'id'])
        placeholders = ', '.join(['?' for _ in range(len(values))])
        query = text(f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})")
        db.session.execute(query, values)
        db.session.commit()
        
        # Fetch the newly created item
        last_id = db.session.execute(text(f"SELECT last_insert_rowid() FROM {table_name}")).scalar()
        new_item_query = text(f"SELECT * FROM {table_name} WHERE id = ?")
        new_item = dict(zip(columns, db.session.execute(new_item_query, [last_id]).fetchone()))
        
        return render_template('item_row.html', item=new_item, table_name=table_name, columns=columns)
    
    return render_template('create.html', table_name=table_name, columns=columns)

@app.route('/update/<table_name>/<int:id>', methods=['GET', 'POST'])
def update_item(table_name, id):
    if table_name not in get_tables():
        return "Table not found", 404
    
    columns = get_columns(table_name)
    query = text(f"SELECT * FROM {table_name} WHERE id = ?")
    item = dict(zip(columns, db.session.execute(query, [id]).fetchone()))
    
    if request.method == 'POST':
        set_clause = ', '.join([f"{col} = ?" for col in columns if col != 'id'])
        values = [request.form.get(col) for col in columns if col != 'id'] + [id]
        query = text(f"UPDATE {table_name} SET {set_clause} WHERE id = ?")
        db.session.execute(query, values)
        db.session.commit()
        
        # Fetch the updated item
        updated_item_query = text(f"SELECT * FROM {table_name} WHERE id = ?")
        updated_item = dict(zip(columns, db.session.execute(updated_item_query, [id]).fetchone()))
        
        return render_template('item_row.html', item=updated_item, table_name=table_name, columns=columns)
    
    return render_template('update.html', item=item, table_name=table_name, columns=columns)

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