# airflow/Dockerfile
FROM apache/airflow:2.9.2-python3.9

ARG AIRFLOW_VERSION=2.9.2
ARG PYTHON_VERSION=3.9
# URL constraint file bisa berubah jika struktur repo Airflow berubah, cek selalu dokumentasi Airflow
ENV CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

# Test 1 (opsional, bisa di-skip jika sudah yakin base image oke)
RUN echo ">>> TEST 1: BEFORE pip install" && \
    echo "User: $(whoami)" && \
    echo "Path: $PATH" && \
    echo "Location of airflow: $(which airflow)" && \
    echo "Airflow version output:" && \
    airflow version && \
    echo ">>> TEST 1 COMPLETED SUCCESSFULLY"

COPY requirements_airflow.txt /tmp/requirements_airflow.txt

RUN echo ">>> INSTALLING provider packages with constraints from /tmp/requirements_airflow.txt" && \
    pip install --no-cache-dir -r /tmp/requirements_airflow.txt --constraint "${CONSTRAINT_URL}" && \
    echo ">>> PROVIDER PACKAGES INSTALLATION COMPLETED"

RUN echo ">>> CHECKING Python package dependencies with pip check" && \
    pip check && \
    echo ">>> PIP CHECK COMPLETED"

# Test 2
RUN echo ">>> TEST 2: AFTER pip install AND pip check" && \
    echo "User: $(whoami)" && \
    echo "Path: $PATH" && \
    echo "Attempting to find airflow with 'which':" && \
    which airflow && \
    echo "Attempting to get airflow version:" && \
    airflow version && \
    echo ">>> TEST 2 COMPLETED SUCCESSFULLY"