#!/bin/bash
# Sample AL2 user-data with known AL2023 breakage
set -eux

yum update -y
amazon-linux-extras install nginx1 -y
yum install -y python2 httpd

# ntp is gone in AL2023
systemctl enable ntpd
systemctl start ntpd

# python2 shebang
cat > /usr/local/bin/report.py <<'EOF'
#!/usr/bin/python
print "hello"
EOF
chmod +x /usr/local/bin/report.py

# iptables service
systemctl enable iptables
systemctl disable selinux || true