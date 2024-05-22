---

# Project Setup and Usage Guide

## Prerequisites

### AWS CLI Installation
To install the AWS CLI, follow these steps:

```bash
$ sudo yum remove awscli
$ curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
$ unzip awscliv2.zip
$ sudo ./aws/install
```

### Docker and Git Installation
Install Docker and Git, then check Docker's status:

```bash
$ sudo yum install docker git
$ sudo systemctl status docker
$ sudo systemctl start docker
```

### AWS CLI Configuration
Configure the AWS CLI by entering your AWS credentials when prompted:

```bash
$ /usr/local/bin/aws configure
```

You will be asked to enter the following details:
- **AWS Access Key ID**: Your access key ID.
- **AWS Secret Access Key**: Your secret access key.
- **Default region name**: The region you want to use, e.g., `us-east-1`.
- **Default output format**: The output format you prefer, e.g., `json`.

Example:
```plaintext
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-east-1
Default output format [None]: json
```

## Cloning the Repository on EC2

### Steps to Clone the Repository
1. **Navigate to the SSH directory:**
    ```bash
    $ cd ~/.ssh
    ```

2. **Check for existing SSH keys:**
    ```bash
    $ ls -al
    ```

3. **Generate a new SSH key (if necessary):**
    ```bash
    $ ssh-keygen -t rsa -b 4096 -C "mouhcine.elyoubi@cloudlink.us"
    ```

4. **Add SSH key to SSH agent:**
    ```bash
    $ eval "$(ssh-agent -s)"
    $ ssh-add ~/.ssh/id_rsa
    ```

5. **Add SSH key to your GitHub account:**
    - Copy the public key:
        ```bash
        $ cat ~/.ssh/id_rsa.pub
        ```
    - Go to your GitHub account settings, navigate to **SSH and GPG keys**, and add a new SSH key by pasting the copied public key.

6. **Test SSH connection:**
    ```bash
    $ ssh -T git@github.com
    ```
    You should see a message like:
    ```
    Hi username! You've successfully authenticated, but GitHub does not provide shell access.
    ```

7. **Clone the repository:**
    ```bash
    $ git clone git@github.com:elyoubiCL/Repo-of-WorkShop-Feat-Ext-From-Doc.git
    ```

### Troubleshooting SSH Issues

If you encounter a `Permission denied (publickey)` error, follow these steps:

1. **Ensure SSH agent is running:**
    ```bash
    $ eval "$(ssh-agent -s)"
    $ ssh-add ~/.ssh/rsa_workshop
    ```

2. **Test SSH connection again:**
    ```bash
    $ ssh -T git@github.com
    ```

3. **Clone the repository:**
    ```bash
    $ git clone git@github.com:elyoubiCL/Repo-of-WorkShop-Feat-Ext-From-Doc.git
    ```

## Setting Up the Project

### Activate the Virtual Environment
Navigate to the project folder and activate the virtual environment:

```bash
$ source workshop/Scripts/activate
```

## Building and Pushing the Docker Image to ECR

### Commands for Building and Pushing the Container Image
1. **Log in to ECR:**
    ```bash
    $ aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin 403344839207.dkr.ecr.us-east-1.amazonaws.com
    ```

2. **Build the Docker image:**
    ```bash
    $ sudo docker build -t m-elyoubi-dev-feat-ext-from-doc-ecr .
    ```

3. **Tag the Docker image:**
    ```bash
    $ sudo docker tag m-elyoubi-dev-feat-ext-from-doc-ecr:latest 403344839207.dkr.ecr.us-east-1.amazonaws.com/m-elyoubi-dev-feat-ext-from-doc-ecr:latest
    ```

4. **Push the Docker image to ECR:**
    ```bash
    $ sudo docker push 403344839207.dkr.ecr.us-east-1.amazonaws.com/m-elyoubi-dev-feat-ext-from-doc-ecr:latest
    ```

### Environment Variables

- `FOLDER_SPLITED_DOC`: `output/`
- `splited_doc/`

## Dockerfile

Here is the updated Dockerfile for the project:

```Dockerfile
# Python 3.11 Lambda base image
FROM public.ecr.aws/lambda/python:3.11

# Copy all files and directories from the current directory to the working directory in the container
COPY . .
RUN ls -l Lake/
RUN ls -l Extract/
RUN ls -l Transformation/
RUN ls -l lambda_function.py

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Define the command to run your application (you may adjust this according to your entry point)
CMD ["lambda_function.handler"]
```

## AWS IAM Roles

### AWS Lambda Basic Execution Role

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
```

### Amazon S3 Full Access

Attach the AmazonS3FullAccess policy to your role.

### Textract Lambda Role

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "textract:StartDocumentTextDetection",
                "textract:GetDocumentTextDetection",
                "textract:DetectDocumentText",
                "textract:AnalyzeDocument"
            ],
            "Resource": "*"
        }
    ]
}
```

---
