# python3.11 lambda base image
FROM public.ecr.aws/lambda/python:3.11
# copy requirements.txt to container
COPY Extract ./
COPY Lake ./
COPY Transformation ./
COPY workshop ./
COPY requirements.txt ./
COPY utilities.py ./
# installing dependencies
RUN pip3 install -r requirements.txt
# Copy function code to container
COPY lambda_function.py ./

# setting the CMD to your handler file_name.function_name
CMD [ "lambda_function.handler" ]