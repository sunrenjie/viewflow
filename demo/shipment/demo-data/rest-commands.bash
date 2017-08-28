credential=(username='admin' password='admin')

# Now that REST API is not expected to check csrf token, we shall drop csrf token for more precise testing.
x=$(http -p HBhb www.self-signed.cn:8001/api/v1/auth/login/ X-Requested-With:XMLHttpRequest ${credential[0]} ${credential[1]} | \
  sed 's/;//g' | grep '^Set-Cookie:  sessionid=' | awk '{print "Cookie:" $2}')

# start step
http --timeout=3600 --print HhBb http://www.self-signed.cn:8001/api/v1/viewflow/shipment/start/ @start.json $x

# shipment_type; carrier set to Default will lead to an additional step of checking insurance
http --timeout=3600 --print HhBb http://www.self-signed.cn:8001/api/v1/viewflow/shipment/1/shipment_type/3/ carrier:='{"name":"Default"}' $x

# check insurance
http --timeout=3600 --print HhBb http://www.self-signed.cn:8001/api/v1/viewflow/shipment/2/check_insurance/10/ need_insurance:=true $x

# take_extra_insurance
http --timeout=3600 --print HhBb POST http://www.self-signed.cn:8001/api/v1/viewflow/shipment/3/take_extra_insurance/26/ cost=100 company_name=abc $x

# fill post label
http --timeout=3600 --print HhBb http://www.self-signed.cn:8001/api/v1/viewflow/shipment/2/fill_post_label/12/ post_label='very heavy!' $x

# assign task package_goods; no POST data, therefore the explicit POST method
http --timeout=3600 --print HhBb POST http://www.self-signed.cn:8001/api/v1/viewflow/shipment/2/package_goods/8/assign/ $x

# perform package_goods; no field data
http --timeout=3600 --print HhBb POST http://www.self-signed.cn:8001/api/v1/viewflow/shipment/2/package_goods/8/ $x
