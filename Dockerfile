
FROM python:3.12-slim-bookworm

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ARG POSTGRES_JDBC_VERSION=42.7.7

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       openjdk-17-jre-headless \
       bash \
       procps \
       curl \
       ca-certificates \
    && mkdir -p /opt/spark-jars \
    && curl -fsSL \
       "https://jdbc.postgresql.org/download/postgresql-${POSTGRES_JDBC_VERSION}.jar" \
       -o /opt/spark-jars/postgresql-jdbc.jar \
    && rm -rf /var/lib/apt/lists/*

ENV SPARK_CLASSPATH=/opt/spark-jars/postgresql-jdbc.jar

WORKDIR /workspace

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

CMD ["bash", "-lc", "sleep infinity"]
