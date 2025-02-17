import os
import sys
import traceback

def eee(e):
    print('eee')
    # # # 例外情報を取得
    # # exc_type, exc_value, exc_traceback = sys.exc_info()
    # # # スタックトレースを解析
    # # tb = traceback.extract_tb(exc_traceback)
    # # # 最後のトレース情報を取得
    # # last_trace = tb[-1]
    # # # 行番号と関数名を取得
    # # line_number = last_trace.lineno
    # # function_name = last_trace.name

    # # print(f"例外の型: {exc_type.__name__}, 関数名: {function_name}, 行番号: {line_number}")

    # 获取异常信息
    exc_type, exc_value, exc_traceback = sys.exc_info()
    # 解析 traceback
    tb = traceback.extract_tb(exc_traceback)
    last_trace = tb[-1]
    
    # 获取方法名
    method_name = last_trace.name
    
    # 通过 traceback 解析类名（如果有的话）
    class_name = self.__class__.__name__ if 'self' in locals() else "UnknownClass"
    
    print(f"异常类型: {exc_type.__name__}, 类名: {class_name}, 方法名: {method_name}, 行号: {last_trace.lineno}")

    # # 获取异常信息
    # exc_type, exc_value, exc_traceback = sys.exc_info()
    # # 解析 traceback
    # tb = traceback.extract_tb(exc_traceback)
    # last_trace = tb[-1]

    # # 获取方法名
    # method_name = last_trace.name

    # # 通过 traceback 获取 frame
    # frame = inspect.currentframe()
    # while frame:
    #     class_name = frame.f_globals.get("__name__", "UnknownClass")
    #     if "__qualname__" in frame.f_code.co_names:
    #         class_name = frame.f_locals.get("__qualname__", "UnknownClass").split(".")[0]
    #         break
    #     frame = frame.f_back

    # print(f"异常类型: {exc_type.__name__}, 类名: {class_name}, 方法名: {method_name}, 行号: {last_trace.lineno}")
