variable "key_name" {
  description = "A name for the key you are importing."
}

variable "public_key" {
  description = <<DESCRIPTION
Public Key Material.
DESCRIPTION
}

variable "aws_region" {
  description = "AWS region to launch servers."
}

# Ubuntu Precise 12.04 LTS (x64)
variable "aws_amis" {
  default = {
    eu-west-1 = "ami-674cbc1e"
    us-east-1 = "ami-1d4e7a66"
    us-west-1 = "ami-969ab1f6"
    us-west-2 = "ami-8803e0f0"
  }
}
