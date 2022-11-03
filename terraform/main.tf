provider "aws" {
  region = "us-east-1"
}

terraform {
  backend "s3" { # Define a remote bucket (AWS S3)
    bucket = "tec-terraform-backend-aws" # Set your bucket's name
    key    = "titanic_model"         # Set the bucket key
    region = "us-east-1"     # Set the region where the bucket exists
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.37"
    }
  }

  required_version = ">= 1.3.4"
}


# resource "aws_instance" "app_server" {
#   ami           = "05183526bce570b80"
#   instance_type = "t2.micro"

#   tags = {
#     Name = "ExampleAppServerInstance"
#   }
# }
resource "aws_security_group" "sg" {
  description = "Security Group for model serving instance"
  ingress {
    description = "All (security with SSH Key)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "Model Port"
    from_port   = 5002
    to_port     = 5002
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }
}

resource "aws_instance" "serve_model" {
  ami                         = "ami-08c40ec9ead489470"
  instance_type               = "t2.micro"
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.sg.id]
  key_name                    = "terraform_andre"
  user_data = file("ubuntu.sh")
}
output "ec2_global_ip" {
  value = "${aws_instance.serve_model.public_ip}"
}

