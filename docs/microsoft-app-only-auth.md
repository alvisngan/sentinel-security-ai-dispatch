# Microsoft Graph API - App-only Authentication

## App-only Authentication
[Python App-only Auth Tutorial](https://learn.microsoft.com/en-us/graph/tutorials/python-app-only?tabs=aad)

Creating an app with app-only authentication is simple, the problem is by default your app can access **all** users information.

If there is something wrong with the app, or if the app got hacked, it will affect the entire company. It is at the upmost important that your app has limited access to the company's data, and that's where [Role Based Access Control (RBAC)](#role-based-access-control) comes in.

## Role Based Access Control
The [Official RBAC Tutorial](https://learn.microsoft.com/en-us/exchange/permissions-exo/application-rbac) is lacking a lot of information, I recommand giving this document a try.

If you are returning to this tutorial, but you forgot what you have done, you can check your progress following the [Check Progress](#check-progress) section.


### Remove Entra ID `Mail.Read` Permission
The RBAC steps we are taking will add to the permissions already granted to the app.
If the app already has `Mail.Read` permission on Entra ID, which has access to the entire company's mailbox,
configuring the RBAC with the following steps will be useless as the app already has full access.

Therefore, remember to remove the `Mail.Read` permission, including the admin consent, on Entra ID.


### PowerShell Prerequisites
To perform RBAC for your app, you will have to use PowerShell and some specific Mircosoft PowerShell Modules.

#### Microsoft Exchange Online
```powershell
# Install, import, and connect to Microsoft Exchange Online
Install-Module ExchangeOnlineManagement -Scope CurrentUser
Import-Module ExchangeOnlineManagement
Connect-ExchangeOnline -UserPrincipalName <your-admin-upn>  # <your-admin-upn> - your email address
```

#### Microsoft Graph SDK
p.s. this is slow
```powershell
# Install, import, and connect to Microsoft Graph SDK
Install-Module Microsoft.Graph -Scope CurrentUser -Repository PSGallery -Force
Import-Module Microsoft.Graph
Get-InstalledModule Microsoft.Graph # Verify installation
Connect-MgGraph -Scopes Application.Read.All
```

### Terminologies

| Term | Function |
| --- | --- |
| Service Principal | Who the app is |
| Application Role | What the app can do |
| Scope | which mailbox(es) it can do it to |
| Role Assignment | Ties Service Principle, Application Role, and Scope together |

### Creating a New Service Princpal

#### Getting the Object ID
The Object ID from the Entra ID registration page is **NOT** the Object ID for Service Principal, don't ask me why, ask Microsoft. You can use the App ID in `<AppId>` from Entra ID though.

```powershell
# Display app information including the Object ID (Id)
Get-MgServicePrincipalByAppId -AppId <AppId> | Format-List DisplayName,AppId,Id # Get the <AppId> on Entra ID
```

It should output something like this:
```powershell
DisplayName : email_forwarding_test
AppId       : d9d76d59-e12d-4c1a-becb-b4ebdd102126
Id          : dd2c5aa9-84b8-4e73-96a6-1a5201918f25
```

The `Id` field is the ObjectId.

#### Actually Creating a New Service Principal

```powershell
# <ObjectId> is the Id from the previous step
# <name> can be any string, use double quotes, e.g. "email_service_princple"
New-ServicePrincipal -AppId <AppId> -ObjectId <ObjectId> -DisplayName <name>
```

```powershell
# Check service principals from a specific app
Get-ServicePrincipal -Identity "<AppId-or-ObjectId-or-DisplayName>" | Format-List
```

### New Scope
While the [Official RBAC Tutorial](https://learn.microsoft.com/en-us/exchange/permissions-exo/application-rbac) made no mention of creating a new scope, it is necessary for the creating a [new role assignment](#new-role-assignment).

This step is very important, because it is the step where you manage which email address your app has access to.

```powershell
# ’<test-admin-upn>’ - target email address, don't forget the single quotes!
New-ManagementScope `
-Name "<ScopeName>" `
-RecipientRestrictionFilter "PrimarySmtpAddress -eq '<test-mailbox-upn>'"
```


### New Role Assignment

```powershell
# The function parameters are explained in the table below
New-ManagementRoleAssignment [[-Name] <String>] -Role <RoleIdParameter> -App <ObjectID, AppID, or DisplayName> -CustomResourceScope <Management Scope> (or -RecipientAdministrativeUnitScope)
```

| Argument | Optional | Type | Discription |
| --- | --- | --- | --- |
| [[-Name] <String>] | Optional | string | Name for the new assignment |
|-Role <RoleIdParameter> | N | Name, DN, GUID | [*e.g. "Application Mail.Read"](#avaliable-roles)<br/>(The double quote is part of the argument) |
| -App <ObjectID, AppID, or DisplayName> | N | GUID | App ID from Entra ID |
| -CustomResourceScope | | Name, DN, GUID | Scope Name from the [previous section](#new-scope)<br/>e.g. "ForwardingApp-MailRead-Scope" |



[Offical `New-ManagementRoleAssignment` docs](https://learn.microsoft.com/en-us/powershell/module/exchangepowershell/new-managementroleassignment?view=exchange-ps)

#### *Avaliable Roles
Not sure where the `-Roles` inputs are documented, but you cannot just input any strings in that field. To check the avaliable roles, you can use this command:

```powershell
Get-ManagementRole | Where-Object {$_.Name -like "Application *"} | Select-Object Name
```

### Done!
Now you have created a [new service principal]{#new-service-principal], a [new scope](#new-scope), and a [new role assignment](#new-row-assginment),
you have finished the role based access control.

You can test if your app can access a specific email address with this command:
```powershell
# <target-email-address> - the email address you want to check if your app has access to
Test-ServicePrincipalAuthorization -Identity "<AppId|ObjectId|DisplayName>" -Resource "<target-email-address>" | Format-Table
```

## Check Progress
### Connect to Microsoft Exchange Online
If you haven’t already, connect to Microsoft Exchange Online.
```powershell
# Connect to Microsoft Exchange Online
Connect-ExchangeOnline -UserPrincipalName <your-admin-upn>  # <your-admin-upn> - your email address
```

### Service Principal
```powershell
# Check all service principals
Get-ServicePrincipal | Format-Table DisplayName,AppId,ObjectId
```

```powershell
# Check service principals from a specific app
Get-ServicePrincipal -Identity "<AppId-or-ObjectId-or-DisplayName>" | Format-List
```

### Scope
```powershell
# Check all management scopes
Get-ManagementScope | Format-Table Name,ScopeRestrictionType,Exclusive,RecipientFilter
```

```powershell
# Check a specific scope
Get-ManagementScope -Identity "ScopeName" | Format-List
```

### Role Assignment
If you know the `-Role` you assigned during [New Role Assignment](#new-role-assignment), you can use it to narrow the search.
For example if the role you set is `"Application Mail.Read"`, then you can use the following command to see the roles assigned to that privilege.
```powershell
Get-ManagementRoleAssignment -Role "Application Mail.Read" | Format-List Name,Role,RoleAssigneeName,RoleAssigneeType,AssignmentMethod,*Scope*
```

Alternatively if you know the App ID, you can use this to search the roles associated with the app.
```powershell
$sp = Get-ServicePrincipal -Identity "<AppId>"

Get-ManagementRoleAssignment |
    Where-Object {
        $_.RoleAssigneeType -eq "ServicePrincipal" -and
        $_.RoleAssigneeName -eq "$($sp.ObjectId)"
    } |
    Format-Table Name,Role,RoleAssigneeName,RoleAssigneeType,AssignmentMethod,CustomResourceScope
```
