FROM python:3.11-slim

WORKDIR /sandbox

# Create an unprivileged user for executing generated code.
RUN useradd --system --uid 10001 --no-create-home sandbox

# Run all generated code as the unprivileged user.
USER 10001:10001

CMD ["python", "temp_solution.py"]