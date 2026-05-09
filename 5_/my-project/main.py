from pydantic import BaseModel, Field


class WeatherQuery(BaseModel):
    city: str = Field(..., description="City name")
    units: str = Field(..., description="celsius or fahrenheit")
    days_ahead: int = Field(default=0,ge=0,le=7, description="Number of days ahead")


if __name__ == "__main__":
    print("#"*30)
    weather_query = WeatherQuery(city="New York", units="celsius", days_ahead=5)
    print(weather_query)
    print(weather_query.city)

    print("#"*30)
    # coercion
    weather_query = WeatherQuery(city="New York", units="celsius", days_ahead="5")
    print(weather_query)
    print(weather_query.days_ahead)
    print(type(weather_query.days_ahead))
    
    print(WeatherQuery.model_json_schema())

    ##############################################
    # validate json, weather query.model_validate_json
    print("#"*30)
    json_data = """{
        "city": "New York",
        "units": "celsius",
        "days_ahead": 5
    }"""
    print(WeatherQuery.model_validate_json(json_data))

    
