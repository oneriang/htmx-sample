

class FileManager:
    """文件管理类，处理上传、验证"""
    ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.png', '.jpg', '.jpeg', '.gif'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    @staticmethod
    def allowed_file(filename: str) -> bool:
        return os.path.splitext(filename)[1].lower() in FileManager.ALLOWED_EXTENSIONS

    @staticmethod
    async def upload_file(file: UploadFile = File(...)):
        if not FileManager.allowed_file(file.filename):
            return HTMLResponse(f"<div class='error'>Unsupported file type</div>")

        file_path = f"./uploaded/{file.filename}"
        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        return HTMLResponse(f"<div class='success'>File uploaded successfully</div>")

    def validate_file_type(file: UploadFile) -> bool:
        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(file.file.read(1024))
        file.file.seek(0)  # Reset file pointer
        return file_type.split('/')[1] in [ext.lstrip('.') for ext in ALLOWED_EXTENSIONS]

    def validate_file_size(file: UploadFile) -> bool:
        file.file.seek(0, 2)  # Move to the end of the file
        file_size = file.file.tell()  # Get the position (size)
        file.file.seek(0)  # Reset file pointer
        return file_size <= MAX_FILE_SIZE

    # @app.post("/upload", response_class=HTMLResponse)
    def upload_file(
        file: UploadFile = File(...)
    ):
        try:
            # 文件验证
            if not allowed_file(file.filename):
                return HTMLResponse(f"<div class='error'>File type not allowed. Allowed types are: {', '.join(ALLOWED_EXTENSIONS)}</div>")

            # if not validate_file_type(file):
            #     return HTMLResponse("<div class='error'>File content does not match the allowed types</div>")

            if not validate_file_size(file):
                return HTMLResponse(f"<div class='error'>File size exceeds the maximum limit of {MAX_FILE_SIZE / (1024 * 1024)} MB</div>")

            # # 临时保存文件
            # temp_file_path = f"./temp_uploads/{file.filename}"
            # os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
            # with open(temp_file_path, "wb") as buffer:
            #     shutil.copyfileobj(file.file, buffer)

            # 准备事务参数
            transaction_params = {
                "file": file,
                "file_name": file.filename,
                "folder_path": "./uploaded"
            }

            # 执行事务
            try:
                result = TM.execute_transactions(
                    transaction_name='file_operations',
                    params=transaction_params,
                    config_file='file_operations_txn.yaml'
                )

                # # 删除临时文件
                # os.remove(temp_file_path)

                # 根据结果返回适当的响应
                if isinstance(result, dict) and 'filename' in result:
                    PageRenderer.load_page_config()
                    # # # print((gv.component_dict.keys())
                    res = PageRenderer.generate_html(
                        gv.component_dict['file_manager'])
                    res = f'''
                    <div hx-swap-oob="innerHTML:#file-manager">
                        {res}
                    </div>
                    '''
                    return HTMLResponse(res)
                    # return HTMLResponse(f"<div class='success'>File '{result['filename']}' processed successfully</div>")
                else:
                    return HTMLResponse(f"<div class='success'>Transaction completed successfully</div>")

            except HTTPException as he:
                return HTMLResponse(f"<div class='error'>{he.detail}</div>")

            except Exception as e:
                logger.error(f"Error during transaction execution: {str(e)}")
                return HTMLResponse(f"<div class='error'>An error occurred during transaction execution: {str(e)}</div>")

        except Exception as e:
            logger.error(f"Error during file upload: {str(e)}")
            return HTMLResponse(f"<div class='error'>An error occurred during file upload: {str(e)}</div>")

    def get_files():
        files = os.listdir("uploaded")
        return files

    # @app.get("/preview/{filename}", response_class=HTMLResponse)
    async def preview_file(request: Request, filename: str):
        file_path = Path(f"uploaded/{filename}")
        if file_path.is_file():
            if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                res = f'''
                    <div>
                        <h2>Preview: { filename }</h2>
                        <img src="./uploaded/{ filename }" alt="{ filename }" style="max-width:100%;max-height:600px;">
                    </div>
                '''
                return res
        res = f'''
            <div>
                File not found or not supported
            </div>
        '''
        return res
