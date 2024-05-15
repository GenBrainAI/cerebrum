from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class ComplexNumber(BaseModel):
    real: float
    imag: float

class ComplexOperation(BaseModel):
    num1: ComplexNumber
    num2: ComplexNumber

def to_complex(num: ComplexNumber):
    return complex(num.real, num.imag)

@app.post("/complex/add")
def add_complex(operation: ComplexOperation):
    num1 = to_complex(operation.num1)
    num2 = to_complex(operation.num2)
    result = num1 + num2
    return {"result": {"real": result.real, "imag": result.imag}}

@app.post("/complex/subtract")
def subtract_complex(operation: ComplexOperation):
    num1 = to_complex(operation.num1)
    num2 = to_complex(operation.num2)
    result = num1 - num2
    return {"result": {"real": result.real, "imag": result.imag}}

@app.post("/complex/multiply")
def multiply_complex(operation: ComplexOperation):
    num1 = to_complex(operation.num1)
    num2 = to_complex(operation.num2)
    result = num1 * num2
    return {"result": {"real": result.real, "imag": result.imag}}

@app.post("/complex/divide")
def divide_complex(operation: ComplexOperation):
    num1 = to_complex(operation.num1)
    num2 = to_complex(operation.num2)
    if num2 == 0:
        return {"error": "Division by zero is not allowed"}
    result = num1 / num2
    return {"result": {"real": result.real, "imag": result.imag}}
