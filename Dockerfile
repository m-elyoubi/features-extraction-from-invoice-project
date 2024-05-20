# python3.11 lambda base image
FROM public.ecr.aws/lambda/python:3.11

# Copy all files and directories from the current directory to the working directory in the container
COPY . .
# This is for checking 
# RUN ls -l Lake/
# RUN ls -l Extract/
# RUN ls -l Transformation/
# RUN ls -l lambda_function.py
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Define the command to run your application (you may adjust this according to your entry point)
CMD ["lambda_function.handler"]
