FILE(GLOB_RECURSE app_sources 
    ${CMAKE_CURRENT_SOURCE_DIR}/*.c
)

idf_component_register(
    SRCS ${app_sources}
    INCLUDE_DIRS ${CMAKE_CURRENT_SOURCE_DIR}/../include
    REQUIRES 
        driver 
        esp_wifi 
        esp_event 
        esp_netif 
        nvs_flash 
        lwip
)