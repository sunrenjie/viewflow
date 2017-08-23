credential=(username='admin' password='admin')

# login and store the cookies for later use (both sessionid and csrf token)
x=$(http -p HBhb www.self-signed.cn:8001/api/v1/auth/login/ X-Requested-With:XMLHttpRequest ${credential[0]} ${credential[1]} | sed 's/;//g' | \
  awk 'BEGIN{s=""}$1=="Set-Cookie:"{ s = s$2";"; if($2~/^csrftoken=/) { print "__"$2 }}END{print "Cookie:"s}' | \
  sed 's/__csrftoken=/X-CSRFToken:/' | xargs echo)

# Now that REST API is not expected to check csrf token, we shall drop csrf token for more precise testing.
x=$(http -p HBhb www.self-signed.cn:8001/api/v1/auth/login/ X-Requested-With:XMLHttpRequest ${credential[0]} ${credential[1]} | \
  sed 's/;//g' | grep '^Set-Cookie:  sessionid=' | awk '{print "Cookie:" $2}')

# start step
http --timeout=3600 --print HhBb POST http://www.self-signed.cn:8001/api/v1/viewflow/orderit/start/ $x @start.json

# user amend order
http --timeout=3600 --print HhBb POST http://www.self-signed.cn:8001/api/v1/viewflow/orderit/13/user_amend_order/33/ $x vms_amended:=true vms_request_for_review:=true malicious:=true
