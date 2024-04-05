import unittest
from unittest.mock import patch
from sqlalchemy import Table, Column, Integer, String, MetaData
from sqlalchemy.sql import select

from main import build_query, apply_filters, handle_conditions, handle_operator, convert_value

# 创建模拟的表结构
metadata = MetaData()
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String),
    Column("email", String),
)

posts = Table(
    "posts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String),
    Column("content", String),
    Column("user_id", Integer),
)

class TestQueryBuilding(unittest.TestCase):
    def test_build_query(self):
        step = {
            "table": "users",
            "fields": [
                {"field": "username"},
                {"field": "email"}
            ],
            "filter_values": [
                {
                    "type": "and",
                    "conditions": [
                        {
                            "field": "id",
                            "operator": "eq",
                            "value": 1
                        }
                    ]
                }
            ]
        }
        query = build_query(step, users)
        str_query = str(query.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("username", str_query)
        self.assertIn("email", str_query)
        self.assertIn("id = 1", str_query)

    def test_apply_filters(self):
        filter_values = [
            {
                "type": "and",
                "conditions": [
                    {
                        "field": "id",
                        "operator": "eq",
                        "value": 1
                    },
                    {
                        "field": "username",
                        "operator": "like",
                        "value": "%John%"
                    }
                ]
            }
        ]
        query = apply_filters(users.select(), filter_values, users)
        str_query = str(query.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("id = 1", str_query)
        self.assertIn("username LIKE '%John%'", str_query)

    def test_handle_conditions(self):
        conditions = [
            {
                "type": "and",
                "conditions": [
                    {
                        "field": "id",
                        "operator": "eq",
                        "value": 1
                    },
                    {
                        "field": "username",
                        "operator": "like",
                        "value": "%John%"
                    }
                ]
            }
        ]
        filters = handle_conditions(conditions, users)
        str_filters = [str(f.compile(compile_kwargs={"literal_binds": True})) for f in filters]
        self.assertIn("users.id = 1 AND users.username LIKE '%John%'", str_filters)

    def test_handle_operator(self):
        column = users.c.id
        self.assertEqual(str(handle_operator(column, "eq", 1)), "users.id = :id_1")
        self.assertEqual(str(handle_operator(column, "ne", 1)), "users.id != :id_1")
        self.assertEqual(str(handle_operator(column, "lt", 1)), "users.id < :id_1")
        self.assertEqual(str(handle_operator(column, "gt", 1)), "users.id > :id_1")
        self.assertEqual(str(handle_operator(column, "le", 1)), "users.id <= :id_1")
        self.assertEqual(str(handle_operator(column, "ge", 1)), "users.id >= :id_1")

    def test_convert_value(self):
        self.assertEqual(convert_value(users.c.id.type, "1"), 1)
        self.assertEqual(convert_value(users.c.username.type, "John"), "John")

if __name__ == "__main__":
    unittest.main()