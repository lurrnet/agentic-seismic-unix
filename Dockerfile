FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
ENV CWPROOT=/opt/cwp
ENV PATH="${CWPROOT}/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ make libc6-dev libtirpc-dev tcsh \
    python3 python3-pip ca-certificates curl wget file \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir -p "${CWPROOT}"
COPY source/cwp_su_all_*.tgz /tmp/su.tgz
RUN tar -xzf /tmp/su.tgz -C "${CWPROOT}" && rm /tmp/su.tgz
WORKDIR ${CWPROOT}/src
RUN test -f configs/Makefile.config_Linux_Ubuntu_22.04 && cp configs/Makefile.config_Linux_Ubuntu_22.04 Makefile.config
# Make SU license prompt non-interactive inside Docker build.
# "more" consumes stdin during a non-TTY Docker build, so replace it with cat.
RUN sed -i 's|more ./LEGAL_STATEMENT|cat ./LEGAL_STATEMENT|' license.sh \
    && printf "y\n\ny\nn\n" | make install
RUN command -v segyread && command -v segyclean && command -v surange && command -v sufilter && command -v suwind && command -v sustrip
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt
COPY . /app
RUN mkdir -p /data/projects
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD curl -fsS http://127.0.0.1:8501/_stcore/health || exit 1
CMD ["streamlit","run","/app/app.py","--server.address=0.0.0.0","--server.port=8501","--server.headless=true","--browser.gatherUsageStats=false"]
