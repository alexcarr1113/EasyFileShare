var sessionCode;

function update_files(fileList) { // Clear file list and rebuild
    $(".file").remove();
    for (var i = 0; i < fileList.length; i++) {
        var filename = fileList[i][0];
        $("#files").append("<div class='row mb-1 file'><div class='col col-md-6'>" + filename + "</div><div class='col col-md-6'><a href='/"+sessionCode+"/" + filename + "' download><button class='btn btn-outline-primary mx-1'>Download</button></a><button onclick=remove_file('" + filename + "') class='btn btn-outline-danger mx-1'>Remove</button></div></div>");
    }
}

function update_text(userText) { // Update text field with parameter
    $("#textInput").attr("value", userText);
}

function remove_file(filename) { // Sends request to remove file from server
    console.log("removing " + filename);
    console.log(sessionCode);
    $.ajax({
        type: "POST",
        url: "/remove/"+sessionCode+"/" + filename,
        success: function (response) {
            update_files(response["fileList"]);
        },
        error: function (error) {
            console.log(error);
        }
    })
}

async function copy_text(text)
{
    try {
        await navigator.clipboard.writeText(text);
        console.log("copied " + text);
    }
    catch (err) {
        console.log(err);
    }
}

$(document).ready(function () { // Runs when document is loaded

    $("#uploadtext").submit(function (event) { // Copies text in upload field to clipboard when button clicked
        event.preventDefault();
        var copyText = document.getElementById("textInput");
        console.log(copyText);
        copyText.select();
        copyText.setSelectionRange(0,99999);
        copy_text(copyText.value);
    })
    // send ajax req for files and text
    sessionCode = $("#sessioncode").html();
    console.log(sessionCode);
    $.ajax({
        type: "POST",
        url: "/"+sessionCode,
        success: function (response) {
            update_files(response["fileList"]);
            update_text(response["userText"]);
        },
        error: function (error) {
            console.log(error);
        }
    })

    $("#uploadtext").on("focusout", function (event) { // Send text field to server
        user_text = $("#textInput").val();
        $.ajax({ // Send AJAX request
            type: "POST",
            url: "/upload/"+sessionCode,
            contentType: 'application/json; charset=utf-8',
            dataType: "json",
            data: JSON.stringify({ "user_text": user_text }),
            success: function (response) { // If successful replace field value with text
                update_text(response["userText"]);
            },
            error: function (response) {
                console.log(response);
            }
        })
        event.preventDefault();
    })

    $("#uploadfile").on("change", function (event) { // When form is submitted, capture file and create form data object
        var file = $("#fileform")[0];
        var formData = new FormData(file);
        $("#uploadbtn").html("Uploading");
        $("#uploadbtn").attr("class", "w-100 btn btn-danger");
        $.ajax({ // Send AJAX request
            type: "POST",
            url: "/upload/"+sessionCode,
            data: formData,
            processData: false,
            contentType: false,
            cache: false,
            success: function (response) { // If successful, remove current list and rebuild list with new files
                $("#uploadbtn").attr("class", "w-100 btn btn-primary");
                $("#uploadbtn").html("Upload");
                update_files(response["fileList"]);
            },
            error: function (response) {
                $("#uploadbtn").html("Upload failed");
            }
        })
        event.preventDefault();
    })
})