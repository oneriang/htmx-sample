class AuthManager:
    """用户认证管理类"""

    @staticmethod
    def verify_password(plain_password, hashed_password):
        return ConfigManager.pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password):
        return ConfigManager.pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta = None):
        try:
            to_encode = data.copy()
            expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
            to_encode.update({"exp": expire})
            return jwt.encode(to_encode, ConfigManager.SECRET_KEY, algorithm=ConfigManager.ALGORITHM)

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @staticmethod
    async def get_current_user(request: Request):
        token = request.cookies.get("access_token")
        if not token:
            return None
        try:
            payload = jwt.decode(token, ConfigManager.SECRET_KEY, algorithms=[
                                 ConfigManager.ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            return {"username": username}
        except JWTError:
            return none

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(password):
        return pwd_context.hash(password)

    def create_access_token(data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    # async def get_current_user(request: Request, token: Optional[str] = Depends(oauth2_scheme)):
    async def get_current_user(request: Request):

        token = request.cookies.get("access_token")

        if not token:
            return None

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
        # except JWTError:
        #    raise credentials_exception
        except JWTError:
            # 检查请求头，判断是否是 HTMX 请求
            if "HX-Request" in request.headers:
                # 如果是 HTMX 请求，返回 401 错误
                raise credentials_exception
            else:
                # 如果不是 HTMX 请求，重定向到登录页面
                return RedirectResponse(url=f"/login?next={request.url.path}", status_code=302)

        # db = SessionLocal()
        try:
            user = db.execute(select(metadata.tables['Users']).where(
                metadata.tables['Users'].c.Username == username
            )).first()
            if user is None:
                raise credentials_exception
            return user

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

        finally:
            db.close()

    def decode_token(token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            return {"username": username, "role": payload.get("role")}
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    def login_required(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            token = None

            # 首先检查 Authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split()[1]

            # 如果 header 中没有 token，则检查 cookie
            if not token:
                token = request.cookies.get('access_token')

            if not token:
                raise HTTPException(
                    status_code=401, detail="Not authenticated")

            try:
                user = decode_token(token)
                # 将用户信息添加到请求中，以便在路由函数中使用
                request.state.user = user
            except HTTPException:
                raise HTTPException(status_code=401, detail="Invalid token")
            except Exception as e:
                # 例外情報を取得
                exc_type, exc_value, exc_traceback = sys.exc_info()
                # 行番号を取得
                line_number = traceback.extract_tb(exc_traceback)[-1].lineno
                print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
                return None

            return await func(request, *args, **kwargs)
        return wrapper

    @app.get("/login", response_class=HTMLResponse)
    # async def login(request: Request, current_user: dict = Depends(get_current_user)):
    #     """
    #     Handle GET requests to the login page
    #     处理登录页面的GET请求
    #     Args:
    #         request: FastAPI request object
    #         current_user: Current user from JWT token dependency
    #     """
    #     # If user is already logged in, redirect to home page
    #     # 如果用户已经登录，重定向到主页
    #     if current_user:
    #         return RedirectResponse(url="/", status_code=302)
    async def login(request: Request):
        try:
            gv.request = request

            # Load latest configuration
            # 加载最新配置
            ConfigManager.load_data()

            # Load login page configuration
            # 加载登录页面配置
            page_config = PageRenderer.load_page_config('login_config.yaml')

            # Render login page components
            # 渲染登录页面组件
            rendered_components = [generate_html(
                component) for component in page_config['components']]

            template = Template(gv.BASE_HTML)
            return template.render(
                page_title="User Management",
                components=rendered_components,
                min=min
            )

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @app.post("/login")
    async def login(request: Request, response: Response):
        """
        Handle POST requests for login
        处理登录的POST请求
        """
        form_data = await request.form()
        params = {key: value for key, value in form_data.items()}

        try:
            # with SessionLocal() as db:
            result = TM.execute_transactions(
                transaction_name="UserLogin",
                params=params,
                config_file="login_txn.yaml"
            )

            user_data = gv.data.get("user_data", [])

            if not user_data or not verify_password(params['password'], user_data[0]["Password"]):
                return "<div class='alert alert-error'>Incorrect username or password</div>"

            user = user_data[0]
            access_token_expires = timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user["Username"], "role": user["Role"]},
                expires_delta=access_token_expires
            )

            html_response = f"<div class='alert alert-success'>Login successful! Welcome</div>"
            response = HTMLResponse(content=html_response)

            # Set secure cookie with token
            # 设置带有令牌的安全cookie
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,  # Only transmit over HTTPS
                samesite='lax',  # Prevent CSRF
                max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )

            # Set cache control headers to prevent caching of login page
            # 设置缓存控制头以防止登录页面被缓存
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['HX-Redirect'] = '/'

            return response

        except Exception as e:
            return HTMLResponse(content=f"<div class='alert alert-error'>Login failed: {str(e)}</div>")

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @app.middleware("http")
    async def cache_control_middleware(request: Request, call_next):
        try:
            """
            Middleware to handle cache control headers
            处理缓存控制头的中间件
            """
            response = await call_next(request)

            # Add cache control headers for login-related pages
            # 为登录相关页面添加缓存控制头
            if request.url.path in ["/login", "/register"]:
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'

            return response

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @app.get("/logout")
    async def logout(request: Request):
        try:
            logger.info("Logout requested")
            # response = RedirectResponse(url="/login", status_code=302)
            response = HTMLResponse(content='')
            response.headers['HX-Redirect'] = '/login'
            response.delete_cookie(key="access_token")
            logger.info("access_token cookie deleted")
            return response

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @app.get("/register", response_class=HTMLResponse)
    async def register(request: Request):
        try:
            gv.request = request

            ConfigManager.load_data()  # 重新加载配置，确保使用最新的配置

            page_config = PageRenderer.load_page_config('register_config.yaml')

            rendered_components = [generate_html(
                component) for component in page_config['components']]

            template = Template(gv.BASE_HTML)
            return template.render(
                page_title="User Management",
                components=rendered_components,
                min=min
            )

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None

    @app.post("/register", response_class=HTMLResponse)
    async def register(request: Request):
        form_data = await request.form()
        params = {key: value for key, value in form_data.items()}
        params['password'] = get_password_hash(params['password'])
        try:
            with SessionLocal() as db:
                result = TM.execute_transactions(
                    transaction_name="RegisterUser",
                    params=params,
                    config_file="register_txn.yaml"
                )
            # return f"<div class='alert alert-success'>User registered successfully!</div>"
            response = HTMLResponse(content='')
            response.headers['HX-Redirect'] = '/login'
            response.delete_cookie(key="access_token")
            logger.info("access_token cookie deleted")
            return response
        except Exception as e:
            return f"<div class='alert alert-error'>Registration failed: {str(e)}</div>"

        except Exception as e:
            # 例外情報を取得
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # 行番号を取得
            line_number = traceback.extract_tb(exc_traceback)[-1].lineno
            print(f"例外の型: {exc_type.__name__}, 行番号: {line_number}")
            return None
