# Loopxyz Take Home Interview Assignment
I have developed the backend for the problem statement asked for Backend Engineering Intern position. The problem statement asked to create the APIs which will help in report generation of various store being active and inactive.
With this, it will also showcase there uptime in last hour(in mins), last day(in hrs), and last week(in hrs). Similarly it will show downtime last hour(in mins), last hour(in hrs), last week(in hrs).

# Logic Used To Calculate Uptime and Downtime
Let understand with an example.
- There exists a store with id 1, whose start time and end time in local zone is given from 10:00 till 13:00 (24 hr format) on 25th Jan 2023 11:30 which is a Wednesday. In the business hour table, that store start and end time is specified for each day of the week.
- Now the store status table has entries for this store 1 almost every hour, whether the store was active or inactive at that timestamp.
- Assuming during the business hour from start to end local time the store has to be conventionally active, I ignored the active status entry for that store when timestamps seen from the start local time as this just suggest the store is active.
- If there is any inactive entry say at 11:15 when timestamp converted to local time zone, then considering the last hour from 10:30 to 11:30, the dopwntime last hour was calculated as 11:30 -11:15 = 15 mins. Then the uptime last hour is calculated as 60-15=45 min.
- Similarly, for uptime and downtime last day all entries were checked which were inactive. Then total downtime was calculated. That total downtime was subtracted from total business time of that day to get the uptime last day.
- Here from start to inactive state, the time in between goes in uptime, then from inactive to next active/inactive/end state time goes in the downtime. If inactive encountered, then next state active encountered, then from that active state till next active/inactive/end state, the time goes in uptime.

Reference time and date taken in the code: January 25, 2023, 19:30 local time (as all timestamps in the store status table vary from 18th Jan 2023 to 25th Jan 2023) 

# Requirements
- fastapi
- uvicorn
- sqlalchemy
- asyncpg
- pydantic
- python-dotenv
- pytz

# How to run the application
- Clone the github repository
- Pip install all the above given requirements in virtual environment
- use commmand `uvicorn main:app --reload` to start the server
- Initially hit the post api, url: `http://127.0.0.1:8000/trigger_report`
- After the post api hit the get api, url: `http://127.0.0.1:8000/get_report/{report_id}`
- Use the report_id as input (in query params) in the get api which was generated from the post api.


 
