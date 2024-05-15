# This file is a simple calculator that can be used to test the OpenAPI plugin.

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Operation(BaseModel):
    num1: float
    num2: float


@app.post("/add")
def add(operation: Operation):
    return {"result": operation.num1 + operation.num2}


@app.post("/subtract")
def subtract(operation: Operation):
    return {"result": operation.num1 - operation.num2}


@app.post("/multiply")
def multiply(operation: Operation):
    return {"result": operation.num1 * operation.num2}


@app.post("/divide")
def divide(operation: Operation):
    if operation.num2 == 0:
        return {"error": "Division by zero is not allowed"}
    return {"result": operation.num1 / operation.num2}
