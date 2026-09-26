from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\HUNT_AR\HuntAR_v4.3.0\mobile\android\app\src\main\java\com\blackmore\huntar\HuntARNativeBridge.kt")
s=p.read_text(encoding="utf-8")
old='    private val store=HuntARMobileStore(activity)\n'
new=old+'    private val entityClient=HuntAREntityClient(activity,store)\n'
if old not in s: raise SystemExit("store anchor not found")
s=s.replace(old,new,1)
anchor='    @JavascriptInterface fun getMobileSdkStatus():String=activity.nativeMobileSdkJson()\n'
insert='''    @JavascriptInterface fun getEntityStatus():String=entityClient.statusJson()\n    @JavascriptInterface fun setEntityUserAddress(address:String):Boolean=entityClient.setUserEntityAddress(address)\n    @JavascriptInterface fun queueEntityUserAsset(contentSha256:String,sizeBytes:Long,mediaType:String,title:String,assetKind:String,classification:String,metadataJson:String,parentAssetIdsJson:String):String =\n        runCatching{entityClient.queueUserAsset(contentSha256,sizeBytes,mediaType,title,assetKind,classification,metadataJson,parentAssetIdsJson)}\n            .getOrElse{JSONObject().put("accepted",false).put("error",it.message?:"ENTITY asset queue failed").toString()}\n    @JavascriptInterface fun queueEntityEvent(eventType:String,payloadSha256:String,subjectIdsJson:String,objectIdsJson:String):String =\n        runCatching{entityClient.queueEvent(eventType,payloadSha256,subjectIdsJson,objectIdsJson)}\n            .getOrElse{JSONObject().put("accepted",false).put("error",it.message?:"ENTITY event queue failed").toString()}\n'''
if anchor not in s: raise SystemExit("bridge anchor not found")
s=s.replace(anchor,anchor+insert,1)
p.write_text(s,encoding="utf-8")
print("HUNTAR bridge patched")
