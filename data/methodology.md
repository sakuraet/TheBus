# Route Data Cleaning

`trips.txt` gives the parameters `direction_id` in binary (ie. 0 & 1), doesn't say which is inbound vs outbound
- look for `headsign` which notates which direction it's headed in (ie. eastbound vs westbound)

`shape.id` gives the unique route shape for all the invariants

## HEA Arrivals JSON API 

http://hea.thebus.org/api_info.asp

`estimated == "1"` is when the bus has gps tracking, we only want to use this
- `estimated == "0"` is when the bus doesn't have gps tracking 
- `estimated == "2"` is when the bus is too far into the future to track/show estimated/scheduled time

### Notes 

- `missing_routes.json` is all the routes that are not registered in thebus api 
  - reason unknown
- the api end point for vehicles is down, it gives 404 
  - reason unknown

### Questions

- many bus routes have service invariants do we track them all? 
  - ex. route "1" "KAHALA MALL", has 3 route variants 
- should we track estimated time vs scheduled time or do it such that when the bus arrives +-0.00001 of the bus stations for long and lat vs scheduled time? 
- should we do something similar to the housing dashboard's "where you can commute to in 30 mins with public transit"? 

### Ideas 

- should we do poverty & council districts overlay? 
  - ie. see which county has the most poverty census tracks, then we can choose a prominent bus station and compare the arrival vs scheduled times? 

