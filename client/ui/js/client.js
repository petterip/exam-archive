/* Implements basic UI functionality in the Exam Archive.
 *
 * @authors:
 * Ari Kairala, Petteri Ponsimaa
 * Department of Information Processing Science
 * University of Oulu
 *
 * The script is based on code made by Ivan Sanchez (from exercise 4 code of resources.py).
 */


/**** DEFINE START CONSTANTS ****/
var DEBUG = true,   // debug is True or False
COLLECTIONJSON = "application/vnd.collection+json",     // Default datatype to be used with hypermedia

// Profiles
User_profile = "http://atlassian.virtues.fi:8090/display/PWP/PWP11#User+profile",
Archive_profile = "http://atlassian.virtues.fi:8090/display/PWP/PWP11#Archive+profile",
Course_profile = "http://atlassian.virtues.fi:8090/display/PWP/PWP11#Course+p",
Exam_profile = "http://atlassian.virtues.fi:8090/display/PWP/PWP11#Exams+profile",
Teacher_profile = "http://atlassian.virtues.fi:8090/display/PWP/PWP11#Teacher+profile",

DEFAULT_DATATYPE = "json",                  // Default datatype
EMPTY_DATATYPE = "text",                    // Datatype for non-hypermedia
ENTRYPOINT = "/exam_archive/api/users/"     // Entry point is UserList/GET
TEACHERS_URL = "/client/data/teachers.json"      // As teachers resource is not implemented, json holdes a static list
LANGUAGES_URL = "/client/data/languages.json"    // As languages resource is not implemented, json holdes a static list
USERTYPES_URL = "/client/data/usertypes.json"    // Available user types are stored in a json list
/**** END CONSTANTS ****/


/**** START RESTFUL CLIENT ***********************************************************************************/

// authorizeUser - Create login form
function authorizeUser() {

    var login_template = {"data": [ {name: "username", value: "", prompt: "User name"},
                                    {name: "password", value: "", prompt: "Password" },
                                    {name: "remember", value: "remember", prompt: "Remember me", type: "checkbox"}] };
    $("#main-content").empty();

    // Create a form with the template values.
    var edit_url = "";
	$form = createFormFromTemplate(edit_url, "login_form", "Login", handleLogin, login_template)

    // Print the form
    $("#page-header")
          .html("<h1>Log in to Exam Archive</h1>");
    $("#main-content").append($form).show();

   	// Hide non-accessible links
    $(".login-needed").hide();
}

// handleLogin - Passes username and password from login form to tryLogin
function handleLogin(event) {

    // Store user name and password from form into variables
    var username = $("#username_id").val();
    var password = $("#password_id").val();
    var remember_me = $("#remember_id").val();

	if (DEBUG) {
		console.log ("Triggered handleLogin");
	}

	event.preventDefault();     // Avoid default link behaviour

	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
	$("#form-content").empty();

    tryLogin(username, password, remember_me);
	return false; 
}

/* tryLogin - access user information to perform login via resource User/GET
 *
 * INPUT:
 * username     username to be tested for login
 * password     uncrypted password to be tested for login
 * remember_me  save session to HTML5 localStorage: true of false
 *
 */
function tryLogin(username, password, remember_me) {
	var apiurl = ENTRYPOINT + username + "/";
    var password_hash = CryptoJS.SHA256(password);

    console.log("Hashed: " + password_hash);

	return $.ajax({
		url: apiurl,
		headers: getAuthHeader(username, password_hash),
		dataType:DEFAULT_DATATYPE
	}).always(function(){

		// Clear possible old data from list
		$("#list-tr").empty();

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		// Get initial values from the collection
		var links = data.collection.links,
		    items = data.collection.items,
		    user_type = findField(items[0].data, "userType"),
		    archive_list = findLink(links, "archive_list");

		// Point logged user for "Edit profile"-link in usermenu
		$("#edit-profile a").attr("href", ENTRYPOINT + username + "/");
		$("body").addClass(user_type);
		$("#user-name").html("User " + username);

        //alert("Login successful!");
        message("Welcome to Exam archive, "+username+"!", "green");

        // Show links for logged user
        $(".login-needed").show();

        sessionStorage.username = username;
        sessionStorage.password = password_hash;
        sessionStorage.usertype = user_type;

        // If usertype is "Super admin", allow user to have list of all archives
        if(user_type == 'super')
        {
            sessionStorage.entrypoint = archive_list;
            sessionStorage.entrypoint_name = "Archives";

            // If user chosed "Remember me" in login form, store session
            if(remember_me)
                storeSession();
            else
                emptySession();

            // Move on to the archive list
            addNavigationLink("Archives", "archives", archive_list, handleGetArchiveList);
            getArchiveList(archive_list);
        }
        // If user is something else, than "Super admin" show only accessible archive and start from that
        else
        {
            var user_archive = items[0].links[0],
                archive_url = user_archive['href'];

            sessionStorage.entrypoint = archive_url;
            sessionStorage.entrypoint_name = user_archive['name'];
            $("li.super-only").remove();

            // If user chosed "Remember me" in login form, store session
            if(remember_me)
                storeSession();
            else
                emptySession();

            // Move on to the archive
            addNavigationLink(user_archive['name'], "archive", archive_url, handleGetArchiveView);
            getArchiveView(archive_url);
        }

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		// Inform user about the error using an alert message.
		showMessage("Could not login. Please, try again. ");
		delete sessionStorage.username;
		delete sessionStorage.password;
		emptySession();
	});
}

// handleLogout - handler to perform loggin out the user
function handleLogout(event) {

    // Clear all data away and change page header
	$("#page-info").empty();
	$("#page-header").html("<h1>Logging out ...</h1>");
	$("#list-header").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
	$("#form-content").empty();
	$("#main-menu").empty();

	// Hide non-accessible links
	$(".login-needed").hide();
	$("body").removeClass();

    // Remove login credirential from session storage
    delete sessionStorage.username;
    delete sessionStorage.password;
    delete sessionStorage.usertype;
    delete sessionStorage.entrypoint;
    delete sessionStorage.entrypoint_name;

    // Empty HTML5 SessionStorage
    emptySession();

    // Reload to page to start over
    location.reload();
	return false; 
}

/*** USER RESOURCE ***/

// getUserList - Render user list by calling UserList/GET resource
function getUserList() {
	var apiurl = ENTRYPOINT;    // use UserList/GET as the entrypoint

	return $.ajax({
		url: apiurl,
        headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).always(function(){
		//Remove old list of users, clear the form data hide the content information(no selected)
		$("#list-tr").empty();
		$("#list-header").empty();
		$("#main-content").hide();
		$("#form-content").empty().hide();

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		//Extract the users
    	users = data.collection.items;
		for (var i=0; i < users.length; i++){
			var user = users[i];

			var user_data = user.data,
			    user_links = user.links;

			for (var j=0; j<user_data.length;j++){
				if (user_data[j].name=="name"){
					username = user_data[j].value;
				}
				if (user_data[j].name=="userType"){
					user_type = user_data[j].value;
				}
				if (user_data[j].name=="userId"){
					user_id = user_data[j].value;
				}

			}
			// Continue to userlist with extracted data
			appendUserToList(user.href, username, user_type, user_links, user_id);
		}
		// Create New user-button
		$("#list-body").append(makeButton("New user", apiurl, handleAddUser));

        var edit_url = data.collection.href;
        var template = data.collection.template;

        $form = createFormFromTemplate(edit_url, "user-form", "Save", handleSaveNewUser, template)

        // Add the form to DOM
        $("#form-content").append($form);
        $("#form-content").append(makeButton("Cancel", apiurl, handleGetUserList));
        displayMessage();

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		showMessageXHR(jqXHR, "Could not fetch the list of users. Please, try again.");
	});
}

// appendUserToList - Adds data extracted from UserList resource with getUserList to listview
function appendUserToList(apiurl, name, type, archives, id) {
        // Print page header "Users"
        $("#page-header")
              .html("<h1>Users</h1>");
        // First create th-elements including header information to tables thead-element
        $("#list-tr")
              .html("<th>Username</th>"+
                    "<th>User type</th>"+
                    "<th>Accessible archive(s)</th>"+
                    "<th class='admin-only'>Action</th>"
                    );
        // Then print information to inside tables tbody-element
        var $user = $(
                    "<tr>"+
                            "<td>"+
                                name+
                            "</td>"+
                             "<td>"+
                                type+
                            "</td>"+
                            "<td>"+
                                userArchives(archives)+
                            "</td>"+
                            "<td class='admin-only'>"+
                                // Edit user-link in the right end of every row
                                "<a class='edit-user' href='"+apiurl+"'>Edit user"+"</a>"+
                            "</td>"+
                        "</tr>"
					);

	//Add table elements to list in index.html
	$("#list-body").append($user);
	return $user;
}

// handleGetUserList - handler of getUserList, when Users-link in Usermenu is activated
function handleGetUserList(event) {
	if (DEBUG) {
		console.log ("Triggered handleGetUserList")
	}
	event.preventDefault();//Avoid default link behaviour

    // Clear old data
	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
	$("#form-content").empty();

    getUserList($(this).attr("href"));
	return false; 
}

// getUserEdit - Create a form to edit details of an user
function getUserEdit(apiurl, handler) {
	return $.ajax({
		url: apiurl,
		headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).always(function(){
		//Remove old information, clear the form data hide the content information(no selected)
		$("#form-content").empty();
		$("#main-content").hide();

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		// Create a form from the template with initial values from the collection item
		var template = data.collection.template;
		var links = data.collection.links;
		var initial_data = data.collection.items[0].data;
		var edit_url = data.collection.href;
		var username = findField(data.collection.items[0].data, "name");

		$form = createFormFromTemplate(edit_url, "user-form", "Save", handler, template, initial_data)

		// Print page header "Edit archive and page info"
        $("#page-header").html("<h1>Edit user "+username+" profile</h1>");
        $("#page-info").html("Edit user details and click Save-button to confirm changes. "+
        "Information marked with asterix (*) is required.");

        // Add the form to DOM
		$("#form-content").append($form);
		$("#form-content").append(makeButton("Cancel", findLink(links, "user_list"), handleGetUserList));

        // Show Delete user-button, if usertype is "Super admin"
        if (sessionStorage.usertype == 'super')
        {
        $("#form-content").append(makeButton("Remove user", edit_url, handleDeleteUser));
        }
		$("#form-content").show();
		displayMessage();

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		showMessage("Could not fetch the list of users. Please, try again.");
	});
}

// addUser
function addUser(apiurl, template){
	templateData = JSON.stringify(template);
	if (DEBUG) {
		console.log ("REQUEST USER/POST: template:",template);
	}
	return $.ajax({
		url: apiurl,
		type: "POST",
		dataType:EMPTY_DATATYPE,
		headers: getAuthHeader(),
		data:templateData,
		processData:false
	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED USER/POST RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		message("User successfully added");

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED USER/POST ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		messageXHR(jqXHR,"Could not create new user. ");
		console.log(jqXHR);
	});
}

// handleAddUser
function handleAddUser(event) {
	if (DEBUG) {
		console.log ("Triggered handleAddUser")
	}
	event.preventDefault();//Avoid default link behaviour

	// Clear old data from header, list and form
	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
	$("#form-content").show();

	return false; 
}

// handleSaveNewUser
function handleSaveNewUser(event){
	var $form = $(this);
	var template = serializeFormTemplate($form);
	var url = $form.attr("action");
	var pwd1 = $form.find("#accessCode_id").val();
	var pwd2 = $form.find("#confirm_id").val();

	if (DEBUG) {
		console.log ("Triggered handleSaveNewUser")
	}

    if(pwd1 != pwd2)
        showMessage("Passwords do not match.");
    else
    {
        var pwd_hash = CryptoJS.SHA256(pwd1).toString();
        setField(template.template.data, "accessCode", pwd_hash);
        addUser(url, template);
        getUserList($("#users a").attr("href"));
	}
	event.preventDefault();
	return false; //Avoid executing the default submit
}

// deleteUser
function deleteUser(apiurl){
	if (DEBUG) {
		console.log ("REQUEST USER/DELETE: ",apiurl);
	}
	return $.ajax({
		url: apiurl,
		type: "DELETE",
		dataType:EMPTY_DATATYPE,
		headers: getAuthHeader(),
	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED USER/DELETE RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		alert ("User successfully removed");

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED USER/DELETE ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		alert ("Could not delete user");
	});
}

// handleDeleteUser
function handleDeleteUser(event) {
	if (DEBUG) {
		console.log ("Triggered handleGetUserList")
	}
	event.preventDefault();//Avoid default link behaviour

	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
	$("#form-content").empty();

    deleteUser($(this).attr("href"));
	getUserList($("#users a").attr("href"));
	return false; 
}

// editUser
function editUser(apiurl, template)
{
    templateData = JSON.stringify(template);
    if (DEBUG) {
		console.log ("REQUEST USER/PUT: template:",templateData);
	}
	$.ajax({
		url: apiurl,
		type: "PUT",
		dataType:EMPTY_DATATYPE,
		headers: getAuthHeader(),
		data:templateData,
		processData:false,
		contentType: COLLECTIONJSON+";"+User_profile,

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED USER/PUT RESPONSE: data:",data,"; textStatus:",textStatus)
		}

		// Inform the user that the profile was successfully updated.
        alert ("The user has been updated");

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED USER/PUT ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}

		// Show an error dialog.
		alert ("Error updating the user information");
	});
}

// handleEditUser
function handleEditUser(event) {
	if (DEBUG) {
		console.log ("Triggered handleEditUser")
	}
	event.preventDefault();//Avoid default link behaviour

	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
	$("#form-content").empty();

    getUserEdit($(this).attr("href"), handleSaveEditedUser);
	return false; 
}

// handleSaveEditedUser
function handleSaveEditedUser(event) {
	var $form = $(this);
	var template = serializeFormTemplate($form);
	var url = $form.attr("action");
	var username = $form.find("#name_id").val();
	var pwd1 = $form.find("#accessCode_id").val();
	var pwd2 = $form.find("#confirm_id").val();

	if (DEBUG) {
		console.log ("Triggered handleSaveUser")
	}

    if(pwd1 != pwd2)
        showMessage("Passwords do not match.");
    else
    {
        var pwd_hash = CryptoJS.SHA256(pwd1).toString();

        setField(template.template.data, "accessCode", pwd_hash);
    	editUser(url, template);

    	if(sessionStorage.username == username)
        	updateSessionPassword(pwd_hash);

       	getUserList($("#users a").attr("href"));
    }
	event.preventDefault();
	return false; //Avoid executing the default submit
}

/* END USER RECOURCE ***/


/* ARCHIVE RESOURCE ***/

// getArchiveList - list all archives, that user can access to
function getArchiveList(apiurl) {
	return $.ajax({
		url: apiurl,
		headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).always(function(){

		//Remove old list of arcchives, clear the form data hide the content information(no selected)
		$("#main-content").hide();
		$("#form-content").empty().hide();

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		//Extract the archives
    	archives = data.collection.items;
		for (var i=0; i < archives.length; i++){
			var archive = archives[i];
			var archive_data = archive.data;

			for (var j=0; j<archive_data.length;j++){
				if (archive_data[j].name=="archiveId"){
					archive_id = archive_data[j].value;
				}
				if (archive_data[j].name=="name"){
					archive_name = archive_data[j].value;
				}
				if (archive_data[j].name=="organisationName"){
					archive_organsation = archive_data[j].value;
				}

			}
			// Move extracted data to archive list
			appendArchiveToList(archive.href, archive_id, archive_name, archive_organsation);
		}

		// Show New archive-button
		$("#list-body").append(makeButton("New archive", apiurl, handleAddArchive));

        var edit_url = data.collection.href;
        var template = data.collection.template;

        // Show form for editing archive
        $form = createFormFromTemplate(edit_url, "archive-form", "Save", handleSaveNewArchive, template)

        // Add the form to DOM
        $("#form-content").append($form);
        $("#form-content").append(makeButton("Cancel", apiurl, returnToPreviousView));
        displayMessage();

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		alert ("Could not fetch the list of archives.  Please, try again");
	});
}

// appendArchiveToList
function appendArchiveToList(url, id, name, organisation) {
        // Print page header "Archives"
        $("#page-header")
              .html("<h1>Archives</h1>");
        $("#page-info")
              .html("<p>Exam archives that you are allowed access to. Please select one to start browsing courses and exams.</p>")
        // Create th-elements including header information to tables thead-element
        $("#list-tr")
              .html("<th>Archive name</th>"+
                    "<th>Organisation</th>"+
                    "<th class='admin-only'>Action</th>"
                    );
        // Then print information to inside tables tbody-element
        var $archive = $(
                    "<tr>"+
                            "<td>"+
                                "<a class='get-archive' href='"+url+"'>"+name+"</a>"+
                            "</td>"+
                             "<td>"+
                                organisation+
                            "</td>"+
                            "<td class='admin-only'>"+
                                "<a class='edit-archive' href='"+url+"'>Edit archive</a>"+
                            "</td>"+
                        "</tr>"
					);

	//Add to the archive list
	$("#list-body").append($archive);
	return $archive;
}

// handleGetArchiveList
function handleGetArchiveList(event) {
    var url = $(this).attr("href");

	if (DEBUG) {
		console.log ("Triggered handleGetArchiveList")
	}
	event.preventDefault();     //Avoid default link behaviour

	//$("ul#main-menu").empty();
	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();

    // Update navigation bar
    console.log("handleGetArchiveList:",url)
    addNavigationLink("Archives", "archives", url, handleGetArchiveList);

    getArchiveList($(this).attr("href"));
	return false; 
}

// handleGetArchiveView
function handleGetArchiveView(event) {
	if (DEBUG) {
		console.log ("Triggered handleGetArchiveView")
	}
	event.preventDefault();//Avoid default link behaviour

	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();

    getArchiveView($(this).attr("href"));
	return false; 
}

// getArchiveView - Show details of a single archive, list courses in the archive and add form for adding new archive
function getArchiveView(apiurl, handler) {
	return $.ajax({
		url: apiurl,
		headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).always(function(){
		//Remove old information, clear the form data hide the content information(no selected)
		$("#form-content").empty();
		$("#main-content").hide();

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		// Create a form from the template with initial values from the collection item
		var item_data = data.collection.items[0].data;
		var course_url = findLink(data.collection.items[0].links, "course_list");
		var template = data.collection.template;
		var links = data.collection.links;
		var initial_data = data.collection.items[0].data;
		var edit_url = data.collection.href;
		var archive_name = findField(item_data,"name");
		var organisationName = findField(item_data,"organisationName");

		var identification_needed = findField(item_data,"identificationNeeded");
		if(identification_needed == 0)
		    identification = "No";
		else
		    identification = "Yes";

        // Print page header
        $("#page-header")
              .html("<h1>Archive "+findField(item_data,"name")+"</h1>");

        $("#page-info")
              .html("<tr>"+
                        "<td>Archive name: "+archive_name+"</td>"+
                        "<td class='admin-only'><a class='edit-archive' href='"+apiurl+"'>Edit archive</a></td>"+
                    "</tr>"+
                    "<tr>"+
                        "<td>Organisation name: "+organisationName+"</td>"+
                        "<td></td>"+
                    "</tr>"+
                    "<tr>"+
                        // Functions around indentification needed value will be implemented later
                        // "<td>Indentification needed: "+identification+"</td>"+
                        "<td></td>"+
                        "<td></td>"+
                    "<tr>");

        // Print list header
        $("#list-header").html("<h4>Courses of the archive</h4>")

        getCourseList(course_url);

		$("#form-content").show();

        addNavigationLink(archive_name, "archive", apiurl, handleGetArchiveView);

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ARCHIVELIST/GET ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		alert ("Could not fetch the list of archives.  Please, try again");
	});
}

// getArchiveEdit - list details of a single archive and add them to a form for editing
function getArchiveEdit(apiurl, handler) {
	return $.ajax({
		url: apiurl,
		headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).always(function(){
		//Remove old information, clear the form data hide the content information(no selected)
		$("#page-header").empty();
		$("#form-content").empty();
		$("#main-content").hide();

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		// Create a form from the template with initial values from the collection item
		var template = data.collection.template;
		var links = data.collection.links;
		var initial_data = data.collection.items[0].data;
		var edit_url = data.collection.href;

		$form = createFormFromTemplate(edit_url, "archive-form", "Save", handler, template, initial_data)

		// Print page header "Edit archive and page info"
        $("#page-header").html("<h1>Edit archive: "+findField(data.collection.items[0].data, "name")+"</h1>");
        $("#page-info").html("Edit archive details and click Save-button to confirm changes. "+
        "Information marked with asterix (*) is required.");

        // Add the form to DOM
		$("#form-content").append($form);
		$("#form-content").append(makeButton("Cancel", findLink(links, "archive_list"), returnToPreviousView));

        if (sessionStorage.usertype == 'super')
        {
        $("#form-content").append(makeButton("Remove archive", edit_url, handleDeleteArchive));
        }
		$("#form-content").show();

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		alert ("Could not fetch the list of archives.  Please, try again");
	});
}


// addArchive
function addArchive(apiurl, template){
	templateData = JSON.stringify(template);
	if (DEBUG) {
		console.log ("REQUEST ARCHIVE/POST: template:",template);
	}
	return $.ajax({
		url: apiurl,
		type: "POST",
		dataType:EMPTY_DATATYPE,
		headers: getAuthHeader(),
		data:templateData,
		processData:false,
		contentType: COLLECTIONJSON+";"+Archive_profile,
	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED ARCHIVE/POST RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		alert ("Archive successfully added");

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ARCHIVE/POST ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		if(jqXHR.status == 405)
		{
		    error("Adding new archive not implemented");
		    //setTimeout(function () { $("#page-info").append("<div class='alert alert-danger' role='alert'>Adding new archive not implemented.</div>"); },500);
		}
		else
    		alert ("Could not create new archive");
	});
}

// handleAddArchive
function handleAddArchive(event) {
	if (DEBUG) {
		console.log ("Triggered handleAddArchive")
	}
	event.preventDefault();//Avoid default link behaviour
	$("#page-header").empty();
	$("#page-info").empty();
	$("#list-header").empty();
	$("#list-tr").empty();
	$("#list-body").empty();

	$("#page-header").html("<h1>Add new archive</h1>");
	$("#page-info").html("Fill all fields and click Save-button to add new archive.");
	$("#form-content").show();

	return false; 
}

// handleSaveNewArchive
function handleSaveNewArchive(event){
	if (DEBUG) {
		console.log ("Triggered handleSaveNewArchive")
	}
	event.preventDefault();
	var $form = $(this);
	var template = serializeFormTemplate($form);
	var url = $form.attr("action");
	addArchive(url, template);

	returnToPreviousView();
	return false; //Avoid executing the default submit
}

// confirmDeleteArchive - Ask confirmation from user, when archive is going to be removed
function confirmDeleteArchive(apiurl)
{
    if (DEBUG) {
		console.log ("Triggered confirmDeleteArchive")
	}
    // Confirmation message
    var r = confirm("Remove archive? All data inside it, will be lost. Continue?");

    // If "Ok" is clicked, continue to delete archive
    if (r == true) {
        deleteArchive(apiurl);
        // if "Cancel" is clicked, return to previous view
    } else {
        returnToPreviousView();
    }
}

// deleteArchive
function deleteArchive(apiurl){
	if (DEBUG) {
		console.log ("REQUEST ARCHIVE/DELETE: ",apiurl);
	}
	return $.ajax({
		url: apiurl,
		type: "DELETE",
		dataType:EMPTY_DATATYPE,
		headers: getAuthHeader()

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED ARCHIVE/DELETE RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		alert ("Archive successfully removed");

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ARCHIVE/DELETE ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		alert ("Could not delete archive");
	});
}

// handleDeleteArchive
function handleDeleteArchive(event) {
	if (DEBUG) {
		console.log ("Triggered handleDeleteArchive")
	}
	event.preventDefault();//Avoid default link behaviour

    // Clear old data from page header, lists and form
	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
	$("#form-content").empty();

    confirmDeleteArchive($(this).attr("href"));
	//getArchiveList($("#archives a").attr("href"));
	returnToPreviousView();
	return false; 
}

// editArchive
function editArchive(apiurl, template)
{
    templateData = JSON.stringify(template);
    if (DEBUG) {
		console.log ("REQUEST ARCHIVE/PUT: template:",templateData);
	}
	$.ajax({
		url: apiurl,
		type: "PUT",
		dataType:EMPTY_DATATYPE,
		headers: getAuthHeader(),
		data:templateData,
		processData:false,
		contentType: COLLECTIONJSON+";"+Archive_profile,

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED ARCHIVE/PUT RESPONSE: data:",data,"; textStatus:",textStatus)
		}

		// Inform the user that the profile was successfully updated.
        alert ("The archive has been updated");

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ARCHIVE/PUT ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}

		// Show an error dialog.
		alert ("Error updating the archive information");
	});
}

// handleEditArchive
function handleEditArchive(event) {
	if (DEBUG) {
		console.log ("Triggered handleEditArchive")
	}
	event.preventDefault();//Avoid default link behaviour

    // Clear old data from page header, lists and form
    $("#page-header").empty();
	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
    $("#form-content").empty();

    getArchiveEdit($(this).attr("href"), handleSaveEditedArchive);
	return false; 
}

// handleSaveEditedArchive
function handleSaveEditedArchive(event) {
	if (DEBUG) {
		console.log ("Triggered handleSaveEditedArchive")
	}
	event.preventDefault();
	var $form = $(this);
	var template = serializeFormTemplate($form);
	var url = $form.attr("action");

	editArchive(url, template);

	returnToPreviousView();
	return false; //Avoid executing the default submit
}

/* END ARCHIVE RECOURCE ***/


/* COURSE RESOURCE ***/

/* getCourseList - list all courses, that belong to the archive */
function getCourseList(apiurl) {
	return $.ajax({
		url: apiurl,
		headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).always(function(){

		//Remove old list of courses, clear the form data hide the content information(no selected)
		$("#main-content").hide();
		$("#form-content").empty().hide();

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		// Extract the courses
    	courses = data.collection.items;

        // If there are no courses yet in the archive...
    	if(courses.length == 0)
    	{
    	    // ...inform the user about it
    	    $("#list-body").append($("<div><em>No courses found.</em></div>"));
    	}
    	// In other case, continue and extract the information
    	else
            for (var i=0; i < courses.length; i++){
                var course = courses[i];
                var course_data = course.data;
                for (var j=0; j<course_data.length;j++){
                    if (course_data[j].name=="courseId"){
                        course_id = course_data[j].value;
                    }
                    if (course_data[j].name=="archiveId"){
                        archive_id = course_data[j].value;
                    }
                    if (course_data[j].name=="courseCode"){
                        course_code = course_data[j].value;
                    }
                    if (course_data[j].name=="name"){
                        course_name = course_data[j].value;
                    }
                    if (course_data[j].name=="creditPoints"){
                        credit_points = course_data[j].value;
                    }
                }
                // Continue to add information to list, with extracted data
                appendCourseToList(course.href, course_id, archive_id, course_code, course_name, credit_points);

            }
        // Do not show New course-button for Basic user
        if (sessionStorage.usertype !== 'basic')
        {
            $("#list-body").append(makeButton("New course", apiurl, handleAddCourse));

            var edit_url = data.collection.href;
            var template = data.collection.template;

            // Show form for adding new course
            $form = createFormFromTemplate(edit_url, "course-form", "Save", handleSaveNewCourse, template)

            // Add the form to DOM
            $("#form-content").append($form);
            $("#form-content").append(makeButton("Cancel", apiurl, returnToPreviousView));
        }
        displayMessage();

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED COURSELIST/GET ERROR: textStatus:",textStatus, ";error:",errorThrown)
       		console.log("jqXHR:",jqXHR);
		}
		if(jqXHR.status == 404)
		{

		}
		else
            //Inform user about the error using an alert message.
            alert ("Could not fetch the list of courses.  Please, try again");
	});
}

// appendCourseToList - Add information extracted with getCourselist to UI
function appendCourseToList(url, course_id, archive_id, course_code, course_name, course_teacher, course_credits) {
        // Create th-elements including header information to tables thead-element
        $("#list-tr")
              .html("<th>Course code</th>"+
                    "<th>Name</th>"+
                    "<th>Credit points</th>"+
                    "<th class='admin-only'>Actions</th>"
                    );

        // Then print information to inside tables tbody-element
        var $course = $(
                    "<tr>"+
                            "<td>"+
                              course_code+
                            "</td>"+
                            "<td>"+
                              "<a class='get-course' href='"+url+"'>"+course_name+"</a>"+
                            "</td>"+
                            "<td>"+
                              credit_points+
                            "</td>"+
                             "<td class='admin-only'>"+
                                "<a class='edit-course' href='"+url+"'>Edit course</a>"+
                            "</td>"+
                       "</tr>"
					);

	//Add to the courses list
	$("#list-body").append($course);
	return $course;
}

// handleGetCourseList
function handleGetCourseList(event) {
    var url = $(this).attr("href");

	if (DEBUG) {
		console.log ("Triggered handleGetCourseList")
	}
	event.preventDefault();//Avoid default link behaviour

	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
	$("#form-content").empty();

    getCourseList(url);
	return false; 
}

// handleGetCourseView
function handleGetCourseView(event) {
	if (DEBUG) {
		console.log ("Triggered handleGetCourseView")
	}
	event.preventDefault();//Avoid default link behaviour

	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();

    getCourseView($(this).attr("href"));
	return false; 
}

// getCourseView - Show course details, in exam list
function getCourseView(apiurl, handler) {
    console.log("getCourseView:",apiurl)

	return $.ajax({
		url: apiurl,
		headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).always(function(){
		//Remove old information, clear the form data hide the content information(no selected)

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		$("#form-content").empty();
		$("#main-content").hide();
		// Create a form from the template with initial values from the collection item
		var item_data = data.collection.items[0].data;
		var exam_list_url = findLink(data.collection.items[0].links, "exam_list");
		var template = data.collection.template;
		var links = data.collection.links;
		var initial_data = data.collection.items[0].data;
		var edit_url = data.collection.href;
        var course_code = findField(item_data,"courseCode");
        var course_name = findField(item_data,"name");
        var course_credits = findField(item_data,"creditPoints");
        var course_teacher = findField(item_data,"teacherName");
        var course_language = findField(item_data,"inLanguage");
        var course_website = findField(item_data,"url");
        var course_description = findField(item_data,"description");

        // Print page header
        $("#page-header")
              .html("<h1>Course "+course_name+"</h1>");

        // Extract course details in table elements and print them in UI
        $("#page-info")
              .html("<tr>"+
                        "<td>Course code: "+course_code+"</td>"+
                        "<td class='admin-only'><a class='edit-course' href='"+apiurl+"'>Edit course</a></td>"+
                    "</tr>"+
                    "<tr>"+
                        "<td>Course name: "+course_name+"</td>"+
                        "<td></td>"+
                    "</tr>"+
                    "<tr>"+
                        "<td>Credit points: "+course_credits+"</td>"+
                        "<td></td>"+
                    "</tr>"+
                    "<tr>"+
                        "<td>Teacher: "+course_teacher+"</td>"+
                        "<td></td>"+
                    "<tr>"+
                    "<tr>"+
                        "<td>Language: "+course_language+"</td>"+
                        "<td></td>"+
                    "<tr>"+
                    "<tr>"+
                        "<td>Website: <a href='"+course_website+"' target='blank'>"+course_website+"</a></td>"+
                        "<td></td>"+
                    "<tr>"+
                    "<tr>"+
                        "<td>Description: "+course_description+"</td>"+
                        "<td></td>"+
                    "<tr>");

        // Show the header for list section
        $("#list-header").html("<h4>Exams of the course</h4>")

        getExamList(exam_list_url);

        // Show the exam list below the course view
		$("#form-content").show();
		
        addNavigationLink(course_name, "course", apiurl, handleGetCourseView);

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		alert ("Could not fetch the list of courses.  Please, try again");
	});
}

// getCourseEdit - render a form to edit details of a single course
function getCourseEdit(apiurl, handler) {
	return $.ajax({
		url: apiurl,
		headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).always(function(){
		//Remove old information, clear the form data hide the content information(no selected)
		$("#form-content").empty();
		$("#main-content").hide();

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		// Create a form from the template with initial values from the collection item
		var template = data.collection.template;
		var links = data.collection.links;
		var initial_data = data.collection.items[0].data;
		var edit_url = data.collection.href;

        // Show form for editing existing course
		$form = createFormFromTemplate(edit_url, "course-form", "Save", handler, template, initial_data)

		// Print page header and page info
        $("#page-header").html("<h1>Edit course: "+findField(data.collection.items[0].data, "name")+"</h1>");
        $("#page-info").html("Edit course details and click Save-button to confirm changes. "+
        "Information marked with asterix (*) is required.");

        // Add the form to DOM
		$("#form-content").append($form);
		$("#form-content").append(makeButton("Cancel", findLink(links, "course_list"), returnToPreviousView));
        $("#form-content").append(makeButton("Remove course", edit_url, handleDeleteCourse));

		$("#form-content").show();

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		alert ("Could not fetch the list of courses.  Please, try again");
	});
}

// addCourse
function addCourse(apiurl, template){
	templateData = JSON.stringify(template);
	if (DEBUG) {
		console.log ("REQUEST COURSE/POST: template:",template);
	}
	return $.ajax({
		url: apiurl,
		type: "POST",
		dataType:EMPTY_DATATYPE,
		headers: getAuthHeader(),
		data:templateData,
		processData:false,
		contentType: COLLECTIONJSON+";"+Course_profile,
	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED COURSE/POST RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		alert ("Course successfully added");

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED COURSE/POST ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		alert ("Could not create new course");
	});
}

// handleAddCourse
function handleAddCourse(event) {
	if (DEBUG) {
		console.log ("Triggered handleAddCourse")
	}
	event.preventDefault();//Avoid default link behaviour

	/// Clear old data from page
	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-header").empty();
	$("#list-body").empty();

	// Add page header, page info and show the form
	$("#page-header").html("<h1>Add new course</h1>");
	$("#page-info").html("Fill all fields and click Save-button to add new course.");
	$("#form-content").show();

	return false; 
}

// handleSaveNewCourse
function handleSaveNewCourse(event){
	var $form = $(this);
	var template = serializeFormTemplate($form);
	var url = $form.attr("action");

	if (DEBUG) {
		console.log ("Triggered handleSaveNewCourse")
	}
	event.preventDefault();
	addCourse(url, template);

    //	getCourseView($("#course a").attr("href"));
    returnToPreviousView();
	return false; //Avoid executing the default submit
}

// deleteCourse
function deleteCourse(apiurl){
	if (DEBUG) {
		console.log ("REQUEST COURSE/DELETE: ",apiurl);
	}
	return $.ajax({
		url: apiurl,
		type: "DELETE",
		dataType:EMPTY_DATATYPE,
		headers: getAuthHeader(),

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED COURSE/DELETE RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		alert ("Course successfully removed");

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED COURSE/DELETE ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		alert ("Could not delete course");
	});
}

// handleDeleteCourse
function handleDeleteCourse(event) {
	if (DEBUG) {
		console.log ("Triggered handleDeleteCourse")
	}
	event.preventDefault();//Avoid default link behaviour

    // Clear old information from the page
	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
	$("#form-content").empty();

    deleteCourse($(this).attr("href"));
	//getCourseList($("#courses a").attr("href"));
	returnToPreviousView();
	return false; 
}

// editCourse
function editCourse(apiurl, template)
{
    templateData = JSON.stringify(template);
    if (DEBUG) {
		console.log ("REQUEST COURSE/PUT: template:",templateData);
	}
	$.ajax({
		url: apiurl,
		type: "PUT",
		dataType:EMPTY_DATATYPE,
		headers: getAuthHeader(),
		data:templateData,
		processData:false,
		contentType: COLLECTIONJSON+";"+Course_profile,

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED COURSE/PUT RESPONSE: data:",data,"; textStatus:",textStatus)
		}

		// Inform the user that the profile was successfully updated.
        alert ("The course has been updated");

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED COURSE/PUT ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}

		// Show an error dialog.
		alert ("Error updating the course information");
	});
}

// handleEditCourse
function handleEditCourse(event) {
	if (DEBUG) {
		console.log ("Triggered handleEditCourse")
	}
	event.preventDefault();//Avoid default link behaviour

    // Clear old information from page
    $("#page-header").empty();
	$("#page-info").empty();
	$("#list-header").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
	$("#form-content").empty();

    getCourseEdit($(this).attr("href"), handleSaveEditedCourse);

	return false; 
}

// handleSaveEditedCourse
function handleSaveEditedCourse(event) {
	if (DEBUG) {
		console.log ("Triggered handleSaveEditedCourse")
	}
	event.preventDefault();
	var $form = $(this);
	var template = serializeFormTemplate($form);
	var url = $form.attr("action");
	editCourse(url, template);

	returnToPreviousView();
	return false; //Avoid executing the default submit
}

/* END COURSE RESOURCE ***/


/* EXAM RESOURCE ***/

// getExamList - list of all exams, that belong to a course */
function getExamList(apiurl) {
	return $.ajax({
		url: apiurl,
		headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).always(function(){
		//Remove old list of exams, clear the form data hide the content information(no selected)
		$("#main-content").hide();
		$("#form-content").empty().hide();

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		//Extract the exams
    	exams = data.collection.items;
		for (var i=0; i < exams.length; i++){
			var exam = exams[i];
			var exam_data = exam.data;

			for (var j=0; j<exam_data.length;j++){
				if (exam_data[j].name=="examinerName"){
					examiner_name = exam_data[j].value;
				}
				if (exam_data[j].name=="date"){
					exam_date = exam_data[j].value;
				}
				if (exam_data[j].name=="associatedMedia"){
				    if(exam_data[j].value == null || exam_data[j].value.length == 0)
				        associated_media = "";
				    else
					    associated_media = exam_data[j].value;
				}
                if (exam_data[j].name=="inLanguage"){
					exam_lang = exam_data[j].value;
				}
			}
			appendExamToList(exam.href, examiner_name, exam_date, associated_media, exam_lang);
		}

		// If user type is not basic, show New exam button
		if (sessionStorage.usertype !== 'basic')
		{
            $("#list-body").append(makeButton("New exam", apiurl, handleAddExam));

            var edit_url = data.collection.href;
            var template = data.collection.template;

            // Show form for adding new exam
            setField(template.data, "associatedMedia", null);
            $form = createFormFromTemplate(edit_url, "new-exam-form", "Save", handleSaveNewExam, template)

            // Add the form to DOM
            $("#form-content").append($form);
            $("#form-content").append(makeButton("Cancel", apiurl, returnToPreviousView));
        }
	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		alert ("Could not fetch the list of exams.  Please, try again");
	});
}

// appendExamToList
function appendExamToList(url, examinerName, exam_date, associated_media, exam_lang)
{
    var filename = associated_media.split("/").pop();
    // Create th-elements including header information to tables thead-element
    $("#list-tr")
          .html("<th>Date</th>"+
                "<th>Examiner</th>"+
                "<th>Language</th>"+
                "<th>File attachment</th>"+
                "<th class='admin-only'>Actions</th>"
                );

    // Then print information to inside tables tbody-element
    var $exam = $(
                "<tr>"+
                        "<td>"+
                          exam_date+
                        "</td>"+
                        "<td>"+
                          examinerName+
                        "</td>"+
                        "<td>"+
                          exam_lang+
                        "</td>"+
                        "<td>"+
                          "<a target='_blank' class='get-file' href='"+associated_media+"'>"+filename+"</a>"+
                        "</td>"+
                        "<td class='admin-only'>"+
                          "<a class='edit-exam' href='"+url+"'>Edit exam</a>"+
                        "</td>"+
                    "</tr>"
                );

	//Add to the courses list
	$("#list-body").append($exam);
	return $exam;
}

// handleGetExamList
function handleGetExamList(event) {
	if (DEBUG) {
		console.log ("Triggered handleGetExamList")
	}
	event.preventDefault();//Avoid default link behaviour

    // Clear old information from page
    $("#page-header").empty();
	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
	$("#form-content").empty();

    getExamList($(this).attr("href"));
	return false; 
}

// handleGetExamView
function handleGetExamView(event) {
	if (DEBUG) {
		console.log ("Triggered handleGetArchiveList")
	}
	event.preventDefault();//Avoid default link behaviour

	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();

    getExamView($(this).attr("href"));
	return false; 
}

// getExamView
function getExamView(apiurl, handler) {
	return $.ajax({
		url: apiurl,
		headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).always(function(){
		//Remove old information, clear the form data hide the content information(no selected)
		$("#form-content").empty();
		$("#main-content").hide();

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		// Create a form from the template with initial values from the collection item
		var item_data = data.collection.items[0].data;
		var course_url = findLink(data.collection.items[0].links, "course_list");
		var template = data.collection.template;
		var links = data.collection.links;
		var initial_data = data.collection.items[0].data;
		var edit_url = data.collection.href;

        // Print page header
        $("#page-header")
              .html("<h1>Course name</h1>");

        $("#page-info")
              .html("<tr>"+
                        "<td>Course code: </td>"+
                        "<td><a class='edit-course' href='"+apiurl+"'>Edit course</a></td>"+
                    "</tr>"+
                    "<tr>"+
                        "<td>Course name: </td>"+
                        "<td></td>"+
                    "</tr>"+
                    "<tr>"+
                        "<td>Teacher: </td>"+
                        "<td></td>"+
                    "<tr>"+
                    "<tr>"+
                        "<td>Language: </td>"+
                        "<td></td>"+
                    "<tr>"+
                    "<tr>"+
                        "<td>Website: </td>"+
                        "<td></td>"+
                    "<tr>"+
                    "<tr>"+
                        "<td>Description</td>"+
                        "<td></td>"+
                    "<tr>");

        $("#list-header")
              .html("<h4>Exams of the course</h4>")

        getExamList(course_url);

		$("#form-content").show();

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		alert ("Could not fetch the list of archives.  Please, try again");
	});
}

// getExamEdit
function getExamEdit(apiurl, handler) {
	return $.ajax({
		url: apiurl,
		headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).always(function(){
		//Remove old information, clear the form data hide the content information(no selected)
		$("#form-content").empty();
		$("#main-content").hide();

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		// Create a form from the template with initial values from the collection item
		var template = data.collection.template;
		var links = data.collection.links;
		var initial_data = data.collection.items[0].data;
		var edit_url = data.collection.href;
		var course_name = $("#course a").html();

		$form = createFormFromTemplate(edit_url, "exam-form", "Save", handler, template, initial_data)

		// Print page header
        $("#page-header").html("<h1>Edit exam: "+findField(data.collection.items[0].data, "date")+
        ", "+course_name+"</h1>");
        $("#page-info").html("Edit exam details and click Save-button to confirm changes. "+
        "Information marked with asterix (*) is required.");

        // Add the form to DOM
		$("#form-content").append($form);
		$("#form-content").append(makeButton("Cancel", findLink(links, "exam_list"), returnToPreviousView));
        $("#form-content").append(makeButton("Remove exam", edit_url, handleDeleteExam));

		$("#form-content").show();

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		alert ("Could not fetch the list of archives.  Please, try again");
	});
}

// addExam
function addExam(apiurl, template){
	templateData = JSON.stringify(template);
	if (DEBUG) {
		console.log ("REQUEST EXAM/POST: template:",template);
	}
	return $.ajax({
		url: apiurl,
		type: "POST",
		dataType:EMPTY_DATATYPE,
		headers: getAuthHeader(),
		data:templateData,
		processData:false,
		contentType: COLLECTIONJSON+";"+Exam_profile,
	}).done(function (data, textStatus, jqXHR){
	    var location = jqXHR.getResponseHeader("Location");
        var file_upload_template = {"data": [ {name: "associatedMedia", value: "", prompt: "Upload exam PDF"} ] };

		if (DEBUG) {
			console.log ("RECEIVED EXAM/POST RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		showMessage("Next, you may attach the PDF file of the exam.", "green");

        $("#form-content").empty();

        console.log("addExam=",location);

        $form = createFormFromTemplate(location, "upload-exam-form", "Add file", handleSaveEditedExam, file_upload_template)

        // Add the form to DOM
        $("#form-content").append($form);
        $("#form-content").append(makeButton("Cancel", location, returnToPreviousView));

        //getExamList($("#exams a").attr("href"));

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED EXAM/POST ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		alert ("Could not create new exam");
	});
}


// handleAddExam
function handleAddExam(event) {
	if (DEBUG) {
		console.log ("Triggered handleAddExam")
	}
	event.preventDefault();//Avoid default link behaviour

    // Clear old information from page
	$("#page-header").empty();
	$("#page-info").empty();
	$("#list-header").empty();
	$("#list-tr").empty();
	$("#list-body").empty();

    // Print page header, page info and show form
	$("#page-header").html("<h1>Add new exam</h1>");
	$("#page-info").html("Fill all fields and click Save-button to add new exam.");
	$("#form-content").show();

	return false; 
}

// handleSaveNewExam
function handleSaveNewExam(event){
	if (DEBUG) {
		console.log ("Triggered handleSaveNewExam")
	}
	var $form = $(this);
	var template = serializeFormTemplate($form);
	var url = $form.attr("action");
	ret = addExam(url, template);

	event.preventDefault();
	//returnToPreviousView();
	return false; //Avoid executing the default submit
}

// deleteExam
function deleteExam(apiurl){
	if (DEBUG) {
		console.log ("REQUEST EXAM/DELETE: ",apiurl);
	}
	return $.ajax({
		url: apiurl,
		type: "DELETE",
		dataType:EMPTY_DATATYPE,
		headers: getAuthHeader()

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED EXAM/DELETE RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		alert ("Exam successfully removed");

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED EXAM/DELETE ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		alert ("Could not delete exam");
	});
}

// handleDeleteExam
function handleDeleteExam(event) {
	if (DEBUG) {
		console.log ("Triggered handleDeleteExam")
	}
	event.preventDefault();//Avoid default link behaviour

	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
	$("#form-content").empty();

    deleteExam($(this).attr("href"));
	returnToPreviousView();
	return false; 
}

// editExam
function editExam(apiurl, template)
{
    templateData = JSON.stringify(template);
    if (DEBUG) {
		console.log ("REQUEST EXAM/PUT: template:",templateData);
	}
	$.ajax({
		url: apiurl,
		type: "PUT",
		dataType:EMPTY_DATATYPE,
		headers: getAuthHeader(),
		data:templateData,
		processData:false,
		contentType: COLLECTIONJSON+";"+Exam_profile,

	}).done(function (data, textStatus, jqXHR){
		if (DEBUG) {
			console.log ("RECEIVED EXAM/PUT RESPONSE: data:",data,"; textStatus:",textStatus)
		}

		// Inform the user that the profile was successfully updated.
        alert ("The exam has been updated");

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED EXAM/PUT ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}

		// Show an error dialog.
		alert ("Error updating the exam information");
	});
}

// handleEditExam
function handleEditExam(event) {
	if (DEBUG) {
		console.log ("Triggered handleEditExam")
	}
	event.preventDefault();//Avoid default link behaviour

    $("#page-header").empty();
	$("#page-info").empty();
	$("#list-header").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
    $("#form-content").empty();

    getExamEdit($(this).attr("href"), handleSaveEditedExam);
	return false; 
}

// handleSaveEditedExam
function handleSaveEditedExam(event) {
	if (DEBUG) {
		console.log ("Triggered handleSaveEditedExam")
	}
	event.preventDefault();
	var $form = $(this);
	var template = serializeFormTemplate($form);
	var url = $form.attr("action");
	editExam(url, template);

   	//getCourseList($("#courses a").attr("href"));
	//getCourseList($(this).attr("href"));
	returnToPreviousView();
	return false; //Avoid executing the default submit
}

/* END EXAM RESOURCE ***/


/* TEACHER RESOURCE - Not implemented yet during the PWP-course,
so teacher information required by other resources is rendered here ***/

// renderTeacherList - Render teacher information
function renderTeacherList($select_obj, defaultValue)
{
	var apiurl = TEACHERS_URL;

	return $.ajax({
		url: apiurl,
        headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).always(function(){
		//Remove old list of users, clear the form data hide the content information(no selected)
		$("#main-content").hide();

	}).done(function (data, textStatus, jqXHR){
	    var output = "";

		if (DEBUG) {
			console.log ("RECEIVED TEACHER RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		//Extract the teacher information
    	teachers = data.collection.items;
		for (var i=0; i < teachers.length; i++) {
			var teacher = teachers[i];
			var teacher_data = teacher.data;
			var selected;

			for (var j=0; j<teacher_data.length;j++){
				if (teacher_data[j].name == "teacherId"){
					teacher_id = teacher_data[j].value;

					if(defaultValue == teacher_id)
					    selected = " selected";
					else
					    selected = "";
				}
				if (teacher_data[j].name == "firstName"){
					teacher_first_name = teacher_data[j].value;
				}
				if (teacher_data[j].name=="lastName"){
					teacher_last_name = teacher_data[j].value;
				}

			}
			// Add teacher information as option to <select>-element
			output += "<option value='" + teacher_id + "'" + selected + ">" + teacher_first_name + " " + teacher_last_name + "</option>";
		}
		$select_obj.append($(output));

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		alert ("Could not fetch the list of teachers.  Please, try again");
	});
}

/* END TEACHER RESOURCE ***/


/* LANGUAGE RESOURCE - ***/

// renderLanguageList
function renderLanguageList($select_obj, defaultValue)
{
	var apiurl = LANGUAGES_URL;

	return $.ajax({
		url: apiurl,
        headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).always(function(){
		//Remove old list of users, clear the form data hide the content information(no selected)
		$("#main-content").hide();

	}).done(function (data, textStatus, jqXHR){
	    var output = "";

		if (DEBUG) {
			console.log ("RECEIVED LANGUAGES RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		//Extract the users
    	languages = data.collection.items;
		for (var i=0; i < languages.length; i++) {
			var language = languages[i];
			var language_data = language.data;
			var selected;

			for (var j=0; j<language_data.length;j++) {
				if (language_data[j].name == "inLanguage"){
					language_id = language_data[j].value;

					if(defaultValue == language_id)
					    selected = " selected";
					else
					    selected = "";
				}
				if (language_data[j].name == "name") {
					language_name = language_data[j].value;
				}
			}
			output += "<option value='" + language_id + "'" + selected + ">" + language_name + "</option>";
		}
		$select_obj.append($(output));

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		alert ("Could not fetch the list of languages.  Please, try again");
	});
}

// renderUserTypeList
function renderUserTypeList($select_obj, defaultValue)
{
	var apiurl = USERTYPES_URL;

	return $.ajax({
		url: apiurl,
        headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).done(function (data, textStatus, jqXHR){
	    var output = "";

		if (DEBUG) {
			console.log ("RECEIVED USERTYPE RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		//Extract the users
    	usertypes = data.collection.items;
		for (var i=0; i < usertypes.length; i++) {
			var usertype = usertypes[i];
			var data = usertype.data;
			var id, name, selected;

			for (var j=0; j<data.length;j++) {
				if (data[j].name == "id"){
					id = data[j].value;

					if(defaultValue == id)
					    selected = " selected";
					else
					    selected = "";
				}
				if (data[j].name == "name") {
					name = data[j].value;
				}
			}
			output += "<option value='" + id + "'" + selected + ">" + name + "</option>";
		}
		$select_obj.append($(output));

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		alert ("Could not fetch the list of usertypes.  Please, try again");
	});
}

// renderArchiveList
function renderArchiveList($select_obj, apiurl, defaultValue)
{

	return $.ajax({
		url: apiurl,
        headers: getAuthHeader(),
		dataType:DEFAULT_DATATYPE
	}).done(function (data, textStatus, jqXHR){
	    var output = "";

		if (DEBUG) {
			console.log ("RECEIVED USERTYPE RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		//Extract the users
    	archives = data.collection.items;
		for (var i=0; i < archives.length; i++) {
			var archive = archives[i];
			var data = archive.data;
			var id, name, selected;

			for (var j=0; j<data.length;j++) {
				if (data[j].name == "archiveId"){
					id = data[j].value;

					if(defaultValue == id)
					    selected = " selected";
					else
					    selected = "";
				}
				if (data[j].name == "name") {
					name = data[j].value;
				}
			}
			output += "<option value='" + id + "'" + selected + ">" + name + "</option>";
		}
		$select_obj.append($(output));

	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		alert ("Could not fetch the list of archives.  Please, try again");
	});
}


/* END LANGUAGE RESOURCE ***/

/**** END RESTFUL CLIENT ***********************************************************************************/


/**** UI HELPERS *****************************/

// makeButton
function makeButton(button_name, url, handler)
{
    var color = { "Save": "btn-success", "Remove archive": "btn-danger", "Remove course": "btn-danger",
                  "Remove exam": "btn-danger", "Remove user": "btn-danger" }

    $button = $("<button></button>");
    $button.attr("value",button_name);
    $button.attr("href",url);
    $button.text(button_name);

    if(typeof color[button_name] != 'undefined')
        $button.addClass("btn " + color[button_name]);
    else
        $button.addClass("btn btn-primary");
    //$list.append($button);

    $button.on("click", handler);
    return $button;
}

// handleEditProfile
function handleEditProfile(event)
{
    var apiurl = ENTRYPOINT + username + "/";

    if (DEBUG) {
		console.log ("Triggered handleEditProfile")
	}
	event.preventDefault();//Avoid default link behaviour

	$("#page-info").empty();
	$("#list-tr").empty();
	$("#list-body").empty();
	$("#form-content").empty();

    getUserEdit($(this).attr("href"), handleSaveEditedUser);
	return false; 
}

// userArchives - Lists archives in "Acccessible archive(s)" of Userlist.
function userArchives(links)
{
        var output = [];

		for (var i=0; i < links.length; i++){
			var link = links[i];

            /* $link = $("<a>" + link['name'] + "</a>");
            $link.attr('href', link['href']);
            $link.attr('rel', link['prompt']); */
            output.push("<a href='" + link['href'] + "' alt='" + link['prompt'] + "' class='get-archive'>" + link['name'] + "</a> ");
		}

        return output.join(", ");
}


/*
Creates a form with the values coming from the template. Based on code by Ivan on exercise 4.

INPUT:
 * url=Value that will be writtn in the action attribute.
 * template=Collection+JSON template which contains all the attributes to be shown.
 * id = unique id assigned to the form.
 * button_name = the text written on associated button. It can be null;
 * handler= function executed when the button is pressed. If button_name is null
   it must be null.

 OUTPUT:
  The form as a jquery element.
*/
function createFormFromTemplate(url,form_id,button_name,handler,template,data)
{
    // List of fields not shown to the end user
    var special_fields = {
                            // Functions related identificatinNeeded value will implemented later
                            'identificationNeeded': 'hidden',
                            'archiveId': 'hidden',
                            'courseId': 'hidden',
                            'examId': 'hidden',
                            'userId':'hidden',
                            //'associatedMedia':'file',
                            'password': 'password',
                         };

	$form=$('<form></form>');
	$form.attr("id",form_id);
	$form.attr("action",url);

	if (template.data) {
		for (var i=0; i<template.data.length; i++){
			var name = template.data[i].name;
			var id = name+"_id";
			var value = template.data[i].value;
			var prompt = template.data[i].prompt;
			var required = template.data[i].required;
			var type = template.data[i].type;
			var usertype = sessionStorage.usertype;

			if(type == "checkbox")
			{
			    // Render a checkbox
			    $div = $('<div></div>');
			    $div.addClass("checkbox");
			    $label = $('<label></label>');
			    $input = $('<input type="checkbox"></input>');
			    $input.attr('id',id);
                if(value){
                    $input.attr('value', value);
                }
                $label.append($input);
                $label.append(prompt);
			    $div.append($label);

			    $form.append($div);
			}
			else
			{
			    if(name == 'teacherId' || name == 'examinerId')
			    {
                    // Render normal input field
                    $input = $('<select></select>');
                    if(typeof data != 'undefined')
                        renderTeacherList($input, findField(data, name));
                    else
                        renderTeacherList($input);
                    //console.log("Out = ",$input);
                }
                else if(name == 'inLanguage')
			    {
                    // Render normal input field
                    $input = $('<select></select>');
                    if(typeof data != 'undefined')
                        renderLanguageList($input, findField(data, name));
                    else
                        renderLanguageList($input);
                }
                else if(name == 'name' && form_id == 'user-form')
                {
                    if(typeof data !='undefined')
                            $input = $('<input type="text" value="'+findField(data, name)+'" disabled>');
                        else
                            $input = $('<input type="text" disabled>');
                }
                else if(name == 'archiveId' && form_id == "user-form" && usertype == 'super')
			    {
			        var apiurl = "/exam_archive/api/archives/";

                    // Render normal input field
                    $input = $('<select></select>');
                    if(typeof data != 'undefined')
                        renderArchiveList($input, apiurl, findField(data, name));
                    else
                        renderArchiveList($input, apiurl);

                    $label_for = $('<label></label>')
                    $label_for.attr("for",id);
                    if(prompt) {
                        $label_for.text(prompt);
                    }
                    $form.append($label_for);
                }
                else if(name == 'accessCode')
                {
                    // Render normal input field
                    $label_for = $('<label></label>')
                    $label_for.attr("for","confirm_id");
                    if(prompt) {
                        $label_for.text(prompt);
                    }
                    $form.append($label_for);

                    $input = $('<input name="accessCode2" id="confirm_id" type="password"></input>');
                    $input.addClass("editable");
                    $input.addClass("form-control");
                    $input.attr('placeholder', "password");
                    $form.append($input);

                    $input = $('<input type="password"></input>');
                    $input.addClass("editable");
                    $input.addClass("form-control");
                    $input.attr('placeholder', "retype the password");
                    $form.append($input);

                    prompt = ""
                    value = ""
                }
                else if(name == 'userType')
                {
                    if (sessionStorage.usertype == 'super')
                    {
                        // Render normal input field
                        $input = $('<select></select>');
                        if(typeof data != 'undefined')
                            renderUserTypeList($input, findField(data, name));
                        else
                            renderUserTypeList($input);
                     }
                     else
                     {
                        if(typeof data !='undefined')
                            $input = $('<input type="text" value="'+findField(data, name)+'" disabled>');
                        else
                            $input = $('<input type="text" disabled>');
                     }
                }
                // Render <textarea> -element for course's description
                else if (name == 'associatedMedia')
                {
                    // Render file input field
                    $input = $('<input name="files[]" id="file-select" type="file">');
                    $input.attr("data-url", url+"upload/");
                    $input.on("change", handleUploadExam);
                }
                else if (name == 'description')
                {
                    $input = $('<textarea></textarea>');
                    if(typeof data != 'undefined')
                    {
                        defaultValue = findField(data, name);
                        $input.val(defaultValue);
                    }
                }
                else
                {
                    if(name in special_fields)
                    {
                        // Render normal input field
                        $input = $('<input type="' + special_fields[name] + '"></input>');
                    }
                    else
                    {
                        // Render normal input field
                        $input = $('<input type="text"></input>');
                    }
                    $input.addClass("editable");
                    $input.attr('placeholder', name);

                    if(typeof data != 'undefined')
                    {
                        defaultValue = findField(data, name);
                        $input.val(defaultValue);
                    }
			    }

                $input.attr('name',name);
                $input.attr('id',id);
                $input.addClass("form-control");

                if(value) {
                    $input.attr('value', value);
                }

                if(required){
                    $input.prop('required',true);
                }

                if(special_fields[name] != 'hidden')
                {
                    $label_for = $('<label></label>')
                    $label_for.attr("for",id);
                    if(prompt){
                        $label_for.text(prompt);
                    }
                    $form.append($label_for);
                }
                $form.append($input);
			}
		}
		if (button_name) {
			$button = $('<button type="submit"></button>');
			$button.attr("value",button_name);
			$button.text(button_name);
    		$button.addClass("btn btn-success btn-block");
			$form.append($button);
			$form.submit(handler);
		}
	}
	$form.attr('autocomplete', 'off');
	return $form;
}

function handleUploadExam(event) {
    var apiurl = $(this).attr("data-url");
	var files = event.target.files;
    var file_data = files[0];       // $('#pic').prop('files')[0];
    var form_data = new FormData();

    $.each(files, function(key, value)
    {
        form_data.append(key, value);
    });

    event.preventDefault();

	if (DEBUG) {
		console.log ("REQUEST EXAMUPLOAD/POST: form_data:",form_data);
	}
	return $.ajax({
		url: apiurl,
		type: "POST",
		dataType:EMPTY_DATATYPE,
		enctype:"multipart/form-data",
		headers: getAuthHeader(),
		data:form_data,
		cache:false,
		processData:false,
		contentType: false // Set content type to false as jQuery will tell the server its a query string request
	}).always(function(){
		//Remove old information, clear the form data hide the content information(no selected)
		//$("#form-content").empty();
		//$("#main-content").hide();

	}).done(function (data, textStatus, jqXHR){
	    var location = jqXHR.getResponseHeader('Location');
        var filename = location.split("/").pop();
        var $file_input = $("#associatedMedia_id");
		if (DEBUG) {
			console.log ("RECEIVED EXAMUPLOAD/POST RESPONSE: data:",data,"; textStatus:",textStatus)
		}
		$file_input.attr("type","text");
		$file_input.val(location);
		$input = $("<input type='text' value='"+filename+"'disabled>");
		$input.insertAfter("#associatedMedia_id");
		$file_input.hide();

        showMessage("File "+filename+" uploaded successfully.","green");
	}).fail(function (jqXHR, textStatus, errorThrown){
		if (DEBUG) {
			console.log ("RECEIVED EXAMUPLOAD/POST ERROR: textStatus:",textStatus, ";error:",errorThrown)
		}
		//Inform user about the error using an alert message.
		alert ("Could not upload exam. Please, try again");
	});
}

/*
Serialize the input values from a given form into a Collection+JSON template.

INPUT:
A form jquery object. The input of the form contains the value to be extracted.

OUPUT:
A Javascript object containing each one of the inputs of the form serialized
following the Collection+JSON template format.

Code based on exercise 4 made by Ivan.
*/
function serializeFormTemplate($form){
	var envelope={'template':{
	              'data':[]
	}};
	// get all the inputs into an array.
    var $inputs = $form.children("input"),
        $selects = $form.children("select");

    $inputs.each(function(){
    	var data = {};
        data.name = this.name;
    	data.value = $(this).val();
    	envelope.template.data.push(data);
    });

    $selects.each(function(){
    	var data = {};
        data.name = this.name;
    	data.value = this.value;
    	envelope.template.data.push(data);
    });
    return envelope;

}

/*
Update navigation bar.
*/
function addNavigationLink(title, id, href, handler) {

    // Remove existing menu items with the same id
    $existing_item = $("ul#main-menu li#"+id).first();
    if($existing_item)
    {
        do
        {
            $next = $existing_item.next();
            $existing_item.remove();
            $existing_item = $next;
        }
        while($existing_item.length > 0);
    }
    //history.replaceState({ href: href }, title, "#");
    $menu_item = $("<li></li>");
    $menu_item.attr("id", id);

/*    if(login_needed == true)
        $menu_item.addClass("login-needed");
*/
    $link = $("<a href='"+href+"'>"+title+"</a>");
    $menu_item.append($link);

    $("ul#main-menu").append($menu_item);
    $link.on("click",handler);

    return $menu_item;
}

function popNavigationView()
{
    $last_menu_item = $("ul#main li").last();

    view = $last_menu_item.attr("id");
    url = $last_menu_item.attr("href");

    $last_menu_item.remove();
}

function returnToPreviousView()
{
    var $last_nav_item = $("ul#main-menu li").last().children();

    $last_nav_item.trigger("click");
}

function getAuthHeader() {

    if(arguments.length == 2)
    {
        username = arguments[0];
        password = arguments[1];
    }
    else
    {
        // Get username and password from sessionStorage
        username = sessionStorage.username;
        password = sessionStorage.password;
    }
    return {"Authorization": "Basic " + btoa(username + ":" + password)};
}

function fetchLoginFromLocalStorage()
{
    // Test whether username has been set
    if (typeof localStorage.username != 'undefined')
    {
        sessionStorage.username = localStorage.username;
        sessionStorage.password = localStorage.password;
        sessionStorage.usertype = localStorage.usertype;
        sessionStorage.entrypoint = localStorage.entrypoint;
        sessionStorage.entrypoint_name = localStorage.entrypoint_name;
        console.log("Found credentials from localStorage - fetched them");
    }
}

function storeSession()
{
    localStorage.username = sessionStorage.username;
    localStorage.password = sessionStorage.password;
    localStorage.usertype = sessionStorage.usertype;
    localStorage.entrypoint = sessionStorage.entrypoint;
    localStorage.entrypoint_name = sessionStorage.entrypoint_name;
    console.log("Stored credentials to localStorage");
}

function updateSessionPassword(pwd)
{
    localStorage.password = pwd;

    if(sessionStorage.password)
        sessionStorage.password = pwd;
}

function findField(item, field)
{
    for (var i=0; i<item.length;i++)
    {
        if (item[i].name == field){
            return item[i].value;
        }
    }
}

function setField(item, field, value)
{
    for (var i=0; i<item.length;i++)
    {
        if (item[i].name == field) {
            if(value != null)
                item[i].value = value;
            else
                item.splice(i,1);
            return;
        }
    }
}

function findLink(links, name)
{
    for (var i=0; i<links.length;i++)
    {
        if (links[i].name == name){
            return links[i].href;
        }
    }
}

function emptySession()
{
    delete localStorage.username;
    delete localStorage.password;
    delete localStorage.usertype;
    delete localStorage.entrypoint;
    delete localStorage.entrypoint_name;
    console.log("Emptied localStorage");
}

function message(msg, color, selector)
{
    var color_class = { "red": "alert-danger", "green": "alert-success", "yellow": "alert-notice" };
    var store_selector = "#page-info",
        store_color = color_class['red'];

    if(typeof selector != 'undefined')
        store_selector = selector;

    if(typeof color != 'undefined')
        store_color = color_class[color];

    localStorage.error_message = msg;
    localStorage.error_message_class = store_color;
    localStorage.error_message_selector = store_selector;
}

function messageXHR(jqXHR, msg, color, selector)
{
    var problem = JSON.parse(jqXHR.responseText);

    message(msg + problem.detail, color, selector);
}

function displayMessage()
{
    if(localStorage.error_message)
    {
        console.log("displayMessage called: ",localStorage.error_message);
        var msg = localStorage.error_message,
            color = localStorage.error_message_class,
            selector = localStorage.error_message_selector;
        var $alert = $("<div class='alert "+color+" role='alert'>"+msg+"</div>");

        // Hide the message after 3 seconds.
        $(selector).append($alert);
        $alert.delay(3000).fadeOut("slow", function () { $(this).remove(); });

        delete localStorage.error_message;
    }
}

function showMessage(msg, color, selector)
{
    message(msg, color, selector);
    displayMessage();
}

function showMessageXHR(jqXHR, msg)
{
    var problem = JSON.parse(jqXHR.responseText);

    showMessage(msg + problem.detail);
}

/*** END UI HELPERS***/

/*** START ON LOAD ***/
//This method is executed when the index.html is loaded.
$(function()
{
    // In case the user chose "Remember me" when logging in, retrieve the user credentials from HTML5 localStorage.
    fetchLoginFromLocalStorage();

    // Check if the user is already authenticated
    if (typeof sessionStorage.username == 'undefined')
    {
        console.log("Session parameter username not found")
        authorizeUser();
    }
    else
    {
        var session_entrypoint = sessionStorage.entrypoint,
            session_entrypoint_name = sessionStorage.entrypoint_name,
            user_type = sessionStorage.usertype,
            username = sessionStorage.username;

        console.log("Session parameter username FOUND, entrypoint=",session_entrypoint, " username=",sessionStorage.username);

        // Point logged user for "Edit profile"-link in usermenu
		$("#edit-profile a").attr("href", ENTRYPOINT + sessionStorage.username + "/");
		$("body").addClass(sessionStorage.usertype);
    	$("#user-name").html("User " + username);

		// Depending on user type show archivelist or courselist after login.
		// Security note: even though a hacker would manipulate the sessionStorage, restAPI checks the user
		// credentials in each request.
		if(user_type == 'super')
        {
    		addNavigationLink(session_entrypoint_name, "archives", session_entrypoint, handleGetArchiveList);

    	    // When loading index.html first time for super user, get list of archives first
            getArchiveList(sessionStorage.entrypoint);
        }
        else
        {
    		addNavigationLink(session_entrypoint_name, "archive", session_entrypoint, handleGetArchiveView);
    		$("li.super-only").remove();

    	    // When loading index.html first time for basic and admin users, get one archive content with list of courses
            getArchiveView(sessionStorage.entrypoint);
        }
    }

	//The main handlers of the links:
	// #users               -> handleGetUserList
	// #logout              -> handleLogout
	// a.get-archivelist    -> handleGetArchiveList
	// a.get-archive        -> handleGetArchiveView
	// a.edit-course        -> handleEditCourse
	// a.edit-user          -> handleEditUser
	// a.get-examlist       -> handleGetExamList
	// a.get-exam           -> handleGetExamView
	// a.edit-exam          -> handleEditExam
	// #edit-profile a      -> handleEditUser

    // Add handlers to navigation
    $("#list-body").on("click", "a.get-archivelist", handleGetArchiveList);
    $("#list-body").on("click", "a.get-archive", handleGetArchiveView);
    $("#list-body,#page-info").on("click", "a.edit-archive", handleEditArchive);

    $("#list-body").on("click", "a.get-courselist", handleGetCourseList);
    $("#list-body").on("click", "a.get-course", handleGetCourseView);
    $("#list-body,#page-info").on("click", "a.edit-course", handleEditCourse);

    $("#list-body,#page-info").on("click", "a.edit-user", handleEditUser);

    $("#list-body").on("click", "a.get-examlist", handleGetExamList);
    $("#list-body").on("click", "a.get-exam", handleGetExamView);
    $("#list-body,#page-info").on("click", "a.edit-exam", handleEditExam);

	// Links of usermenu, in top-right corner of the screen
	$("#edit-profile a").on("click", handleEditUser);
	$("#users").on("click", handleGetUserList);
	$("#logout").on("click", handleLogout);

})
/*** END ON LOAD ***/
