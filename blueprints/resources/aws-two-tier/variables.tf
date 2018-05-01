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
    eu-west-1 = "ami-38708b45"
    us-east-1 = "ami-ee6f5e8b"
    us-west-1 = "ami-fb32279b"
    us-west-2 = "ami-a523b4dd"
  }
}
