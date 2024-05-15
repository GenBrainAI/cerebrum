# Builder stage as before
FROM python:3.11 AS builder
WORKDIR /usr/src/app
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"
COPY . .
RUN pip install --no-cache-dir --upgrade -r requirements.txt
# RUN pip install --upgrade -r requirements.txt

# Test runner stage as before
FROM python:3.11 AS test_runner
WORKDIR /tmp
COPY --from=builder /venv /venv
COPY --from=builder /usr/src/app/tests tests
ENV PATH=/venv/bin:$PATH

# Service stage with corrected COPY command (if applicable)
FROM python:3.11 AS service
WORKDIR /app
COPY --from=test_runner /venv /venv
ENV PATH=/venv/bin:$PATH
COPY . /app
ENV OPENAI_API_KEY "TAKEN FROM ENVIRONMENT VARIABLE"
EXPOSE 8080
CMD ["uvicorn", "src.server.main:app", "--host", "0.0.0.0", "--port", "8080"]
