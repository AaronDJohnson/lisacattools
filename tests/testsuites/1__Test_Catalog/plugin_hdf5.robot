*** Settings ***
Documentation           A test suite for the EMRI and SOBBH plugins
Library                 TestPluginHdf5.py                                   WITH NAME   hdf5

*** Test Cases ***
Test EMRI Plugin
    Check Plugin            EMRI        EmriCatalog

Test SOBBH Plugin
    Check Plugin            SOBBH       SobbhCatalog

*** Keywords ***
Check Plugin
    [Arguments]                     ${prefix}                       ${catalog_class}
    ${cnt}=                         hdf5.Get Number                 ${prefix}
    Should Be Equal As Numbers      ${cnt}                          3
    ${cls}=                         hdf5.Get Catalog Class          ${prefix}
    Should Be Equal                 ${cls}                          ${catalog_class}
    ${names}=                       hdf5.Get Catalogs Name          ${prefix}
    ${expected}=                    Create List                     ${prefix}catalog_week001    ${prefix}catalog_week002    ${prefix}catalog_week003
    Should Be Equal                 ${names}                        ${expected}
    ${detections}=                  hdf5.Get Detections             ${prefix}
    ${expected}=                    Create List                     S1_w3    S2_w3
    Should Be Equal                 ${detections}                   ${expected}
    ${shape}=                       hdf5.Get Samples Shape          ${prefix}    S1_w3
    ${expected}=                    Create List                     ${50}    ${2}
    Should Be Equal                 ${shape}                        ${expected}
    ${differ}=                      hdf5.Get Samples Differ         ${prefix}
    Should Be True                  ${differ}
    ${weeks}=                       hdf5.Get Lineage Weeks          ${prefix}    S1_w3
    ${expected}=                    Create List                     ${1}    ${2}    ${3}
    Should Be Equal                 ${weeks}                        ${expected}
    ${weeks}=                       hdf5.Get Lineage Weeks          ${prefix}    S2_w3
    ${expected}=                    Create List                     ${3}
    Should Be Equal                 ${weeks}                        ${expected}
    ${shape}=                       hdf5.Get Lineage Data Shape     ${prefix}
    ${expected}=                    Create List                     ${150}    ${4}
    Should Be Equal                 ${shape}                        ${expected}
