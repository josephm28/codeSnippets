//
// Joseph Malone, 9/13/2014
//
// This script, when imbeded in a Google Doc spreadsheet, will send an email to emailAddress with a notification
// that there is a new email waiting in the inbox of the user who owns the Google Doc.
// Please go to the end of this document for Setup Instructions.
// Modified from http://ankitmathur111.wordpress.com/2014/01/28/new-gmail-in-inbox-setup-sms-alerts-for-new-gmails-in-your-mailbox/
//

function sendEmailNotification() { 
  try { 
    var emailAddress = "";
    var subject = "";
    var message = "";
    var signature = "";

    var label = GmailApp.getUserLabelByName('sendEmailNotification'); 
    var threads = label.getThreads();
    for (var i = 0; i < threads.length; i++) {
       var originalSubject = threads[i].getFirstMessageSubject();
       MailApp.sendEmail(emailAddress, subject, message+originalSubject+signature);
    }    
    label.removeFromThreads(threads); 
  } catch(err) { 
    Logger.log("Error Occured"+ err.toString()); 
  }
} 

function onOpen() { 
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var menuEntries = [ {name: "Authorize", functionName: "authorize"}, {name: "Stop alerts", functionName: "stopalerts"} ];
  ss.addMenu("Gmail Email Alerts", menuEntries);
}   

function authorize(){}

function stopsmsalerts() { 
  var allTriggers = ScriptApp.getScriptTriggers();
  for(var i=0; i < allTriggers.length; i++) {
    ScriptApp.deleteTrigger(allTriggers[i]);
  }
  Browser.msgBox("Success", "You will not be getting email alerts anymore.",Browser.Buttons.OK); 
}

// ———————————— Setup Instructions ————————————
// ————————————————————————————————————————————————————————————
// Starting the Setup:
// ———————————— Settings in Mailbox ————————————
// 1. Login to your Gmail account.
// 2. Click on the gear icon visible in rightmost corner of the account.
// 3. Click on “Settings” link from the dropdown.
// 4. Now, from the newly loaded page, click on “Labels” menu.
// 5. Scroll to the bottom of the page, click on “Create new label”.
// 6. Name it exactly “sendEmailNotification” and the click on “Create” button from the popup box. The popup should close now.
// 7. Now, from the same menu on which you clicked “Labels”, it’s time to click on “Filters”.
// Now, we will filter the type of email notifications you want to receive. Like, you want to receive only those mails which contain name “Fred,” such filtering can be done here. 
// 8. Again scroll down and reach bottom of the page.
// 9. Click on a link named as “Create a new filter”.
// 10. Now, from the new dropdown which has appeared you need to select the filter you want to make. Let’s say, in the “To” textbox you fill your email id. Which will send notification for every that mail which is delivered on your email id.
// 11. After you have done with filter contents, click on “Create filter with this search >>” which is at the bottom of the dropdown window.
// 12. Now, the dropdown contents should get updated.
// 13. Checkmark the label saying “Apply the Label”.
// 14. Now, from the combo box in front of the label, select the label with exact name as “sendEmailNotification”.
// 15. Now, click on the blue button in the same dropdown which says “Create Filter”. The filter should be created by now.
// ———————————— Settings in Google Doc ————————————
// 1. Now, go to google docs from the same logged-in account. If you can’t find the link, then follow here: https://docs.google.com/‎
// 2. From the left-most menu, click on red colored “Create”, a dropdown will appear. Select “Spreadsheet” from it.
// 3. Now, from the spreadsheet menu, select “Tools” and go to “Script Editor”.
// 4. A new page with a popup will open up. From left menu, select “Spreadsheet”.
// 5. You will be redirected to a new page for writing some code. Don’t worry, I will provide you the code for it :)
// 6. In the code tab named as “Code.gs”, select the prewritten code and brutally delete it. Blank the whole window and color it from the white blood of codes.
// 7. For the code, use what’s here.
// 8. Now, from the window menu, click on “File” and save the file with name exactly “sendEmailNotification”.
// 9. Now, from the same window menu, click on “Run” and from the dropdown select “authorize”.
// 10. Now, close this window and go to the spreadsheet. Close the spreadsheet and reopen it. You will be able to see a new menu as “Get Email Alerts”.
// 11. Click on it and from the dropdown select “Authorize”.
// 12. Close the spreadsheet too.
// 13. Now, you need to reopen the same spreadsheet which you used to copy-paste the script.  Under tools menu, select “Script Editor”.
// 14. Now, in the script window’s menu click on “Resources” and select “Current project’s triggers”. Add a new trigger here according to the frequency you wish to receive the mails.
// 15. You are done with the setup here. Send a test mail to yourself.
