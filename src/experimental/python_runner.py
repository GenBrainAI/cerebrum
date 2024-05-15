import docker
import uuid

def run_python(code, requirements):
    client = docker.from_env()

    # Create a unique container name to avoid conflicts
    container_name = f"python_run_{uuid.uuid4()}"

    # Define the Docker commands to prepare the environment
    docker_commands = f"""
    echo '{requirements}' > /tmp/requirements.txt && \\
    pip install -r /tmp/requirements.txt && \\
    python -c "{code}"
    """

    # Run the container, execute the commands, and remove the container afterward
    try:
        container = client.containers.run(
            "python:3.8", 
            command=["/bin/bash", "-c", docker_commands],
            name=container_name,
            remove=True,  # Ensure the container is removed after execution
            detach=True,  # Run in detached mode
        )
        container.wait()  # Wait for the container to finish executing

        # Get the logs (output) of the container execution
        logs = container.logs()
        return logs.decode("utf-8")
    except docker.errors.ContainerError as e:
        return f"An error occurred while executing the code: {e}"
    finally:
        # Clean up: Remove the container if it hasn't been removed yet
        try:
            client.containers.get(container_name).remove()
        except docker.errors.NotFound:
            pass  # Container already removed

# Example usage
code = "print('Hello from inside a container')"
requirements = ""

print(run_python(code, requirements))
