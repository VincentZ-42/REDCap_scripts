let
    redcapUrl = "university_redcap_url",
    parameters = 
        [
            token="api_token",
            content="report",
            format="json",
            report_id="",
            csvDelimiter="",
            rawOrLabel="label",
            rawOrLabelHeaders="raw",
            exportCheckboxLabel="false",
            exportDataAccessGroups="true",
            returnFormat="json"
        ],
    body = Text.ToBinary(Uri.BuildQueryString(parameters)),
    options = 
        [
            Headers = [#"Content-type"="application/x-www-form-urlencoded"], 
            Content = body
        ],
    Source = Json.Document(Web.Contents(redcapUrl , options)),
    #"Converted to Table" = Table.FromList(Source, Splitter.SplitByNothing(), null, null, ExtraValues.Error)
in
    #"Converted to Table"
