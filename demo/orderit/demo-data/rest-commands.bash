credential=(username='admin' password='admin')

# login and store the cookies for later use
x=$(http -p HBhb www.self-signed.cn:8001/api/v1/auth/login/ X-Requested-With:XMLHttpRequest ${credential[0]} ${credential[1]} | sed 's/;//g' | \
  awk 'BEGIN{s=""}$1=="Set-Cookie:"{ s = s$2";"; if($2~/^csrftoken=/) { print "__"$2 }}END{print "Cookie:"s}' | \
  sed 's/__csrftoken=/X-CSRFToken:/' | xargs echo)

# start step
http --timeout=3600 --print HhBb POST http://www.self-signed.cn:8001/api/v1/viewflow/orderit/start/ $x @start.json
