class CURDManager:

    @app.get("/create", response_class=HTMLResponse)
    @staticmethod
    async def create_form(request: Request):
        try:
            gv.request = request

            table_name = None
            id = None

            query_params = dict(request.query_params)

            if 'table_name' in query_params:
                table_name = query_params['table_name']

            if 'id' in query_params:
                id = query_params['id']

            if table_name is None:
                table_name = 'users'

            table_config = ConfigManager.get_table_config(table_name)

            primary_key = None

            if True:

                component_id = None

                if 'component_id' in query_params:
                    component_id = query_params['component_id']

                if component_id is None:
                    component_id = 'form_create'

                PageRenderer.load_page_config()

                gv.component_dict[component_id]['config'] = {
                    'table_name': table_name,
                    'id': id,
                    'data': {},
                    'primary_key': primary_key,
                    'table_config': table_config
                }

                return generate_html(gv.component_dict[component_id])

            raise HTTPException(status_code=404, detail="Item not found")

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @app.post("/create/{table_name}")
    @staticmethod
    async def create_item(table_name: str, request: Request):
        try:
            table = None
            if table_name in metadata.tables:
                table = metadata.tables[table_name]
            if table is None:
                raise HTTPException(status_code=404, detail="Table not found")

            form_data = await request.form()
            data = {key: value for key, value in form_data.items()
                    if key in table.columns.keys()}

            table_config = ConfigManager.get_table_config(table_name)

            for c in table_config['columns']:
                if c['primary_key'] == 1:
                    if 'autoincrement' in c and c['autoincrement'] == True:
                        data[c['name']] = None

            data_copy = copy.deepcopy(data)

            for key in data_copy:
                auto_update = False
                for c in table_config['columns']:
                    if key == c['name']:
                        if 'auto_update' in c.keys():
                            if c['auto_update'] == True:
                                auto_update = True
                                break

                if auto_update:
                    data[key] = datetime.now()
                else:
                    data[key] = convert_value(table.c[key].type, data[key])

            try:
                with SessionLocal() as session:
                    stmt = insert(table).values(**data)
                    session.execute(stmt)
                    session.commit()
                return templates.TemplateResponse("table_content.html", {
                    "request": request,
                    "table_name": table_name,
                    "columns": table.columns.keys(),
                    "rows": session.execute(select(table)).fetchall(),
                    "primary_key": ConfigManager.get_primary_key(table),
                    "page": 1,
                    "page_size": 10,
                    "total_items": session.execute(select(func.count()).select_from(table)).scalar(),
                    "total_pages": 1,
                    "search": "",
                })
            except SQLAlchemyError as e:
                return {"success": False, "message": str(e)}

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @app.get("/edit", response_class=HTMLResponse)
    @staticmethod
    async def edit_form(request: Request):
        try:
            gv.request = request

            table_name = None
            id = None

            query_params = dict(request.query_params)

            if 'table_name' in query_params:
                table_name = query_params['table_name']

            if 'id' in query_params:
                id = query_params['id']

            if table_name is None:
                table_name = 'users'

            if id is None:
                id = 22

            table_config = ConfigManager.get_table_config(table_name)
            table = metadata.tables[table_name]

            primary_key = next(
                (c['name'] for c in table_config['columns'] if c['primary_key'] == 1), None)

            if primary_key is None:
                primary_key = ConfigManager.get_primary_key(table)

            with SessionLocal() as session:
                stmt = select(table).where(getattr(table.c, primary_key) == id)
                result = session.execute(stmt).fetchone()._asdict()

            if result:

                data = dict(result)

                component_id = None

                if 'component_id' in query_params:
                    component_id = query_params['component_id']

                if component_id is None:
                    component_id = 'form_edit'

                PageRenderer.load_page_config()

                gv.component_dict[component_id]['config'] = {
                    'table_name': table_name,
                    'id': id,
                    'data': data,
                    'primary_key': primary_key,
                    'table_config': table_config
                }

                return generate_html(gv.component_dict[component_id])

            raise HTTPException(status_code=404, detail="Item not found")

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @app.post("/edit/{table_name}/{id}")
    @staticmethod
    async def edit_item(table_name: str, id: str, request: Request):
        try:
            table = None
            if table_name in metadata.tables:
                table = metadata.tables[table_name]
            if table is None:
                raise HTTPException(status_code=404, detail="Table not found")

            primary_key = ConfigManager.get_primary_key(table)
            form_data = await request.form()
            data = {key: value for key, value in form_data.items()
                    if key in table.columns.keys()}

            table_config = ConfigManager.get_table_config(table_name)

            data_copy = copy.deepcopy(data)

            for key in data_copy:
                auto_update = True
                for c in table_config['columns']:
                    if key == c['name']:
                        if 'auto_update' in c.keys():
                            if c['auto_update'] == False:
                                auto_update = False
                                break

                if auto_update:
                    data[key] = convert_value(table.c[key].type, data[key])
                else:
                    del data[key]

            try:
                with SessionLocal() as session:
                    stmt = update(table).where(
                        getattr(table.c, primary_key) == id).values(**data)
                    session.execute(stmt)
                    session.commit()
                    return ''

            except SQLAlchemyError as e:
                return {"success": False, "message": str(e)}

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @app.get("/delete", response_class=HTMLResponse)
    @staticmethod
    async def delete_form(request: Request):
        try:
            gv.request = request

            table_name = None
            id = None

            query_params = dict(request.query_params)

            if 'table_name' in query_params:
                table_name = query_params['table_name']

            if 'id' in query_params:
                id = query_params['id']

            if table_name is None:
                table_name = 'users'

            table_config = ConfigManager.get_table_config(table_name)

            table = metadata.tables[table_name]

            primary_key = ConfigManager.get_primary_key(table)

            with SessionLocal() as session:
                stmt = select(table).where(getattr(table.c, primary_key) == id)
                result = session.execute(stmt).fetchone()._asdict()

            if result:

                data = dict(result)

                component_id = None

                if 'component_id' in query_params:
                    component_id = query_params['component_id']

                if component_id is None:
                    component_id = 'form_delete'

                PageRenderer.load_page_config()

                gv.component_dict[component_id]['config'] = {
                    'table_name': table_name,
                    'id': id,
                    'data': data,
                    'primary_key': primary_key,
                    'table_config': table_config
                }

                return generate_html(gv.component_dict[component_id])

            raise HTTPException(status_code=404, detail="Item not found")

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @app.post("/delete/{table_name}/{id}")
    @staticmethod
    async def delete_item(table_name: str, id: str):
        try:
            table = None
            if table_name in metadata.tables:
                table = metadata.tables[table_name]
            if table is None:
                raise HTTPException(status_code=404, detail="Table not found")

            primary_key = ConfigManager.get_primary_key(table)

            try:
                with SessionLocal() as session:
                    stmt = delete(table).where(
                        getattr(table.c, primary_key) == id)
                    session.execute(stmt)
                    session.commit()
                # return {"success": True, "message": "Item deleted successfully"}
                return "Item deleted successfully"
            except SQLAlchemyError as e:
                return {"success": False, "message": str(e)}

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None
