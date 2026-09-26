package com.blackmore.searchar

import android.content.Context
import com.blackmore.niki.runtime.NikiMobileRuntime
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Environment
import android.webkit.JavascriptInterface
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

class SearchARNativeBridge(private val activity:MainActivity){
    private val prefs=activity.getSharedPreferences("searchar_mobile",Context.MODE_PRIVATE)
    private val store=SearchARMobileStore(activity)
    private val pttProof=PttDeviceProof()
    private val pttAudio=PttAudioEngine(activity){apiBase()}
    private fun apiBase()=prefs.getString("api_base","")?.trim()?.trimEnd('/')?:""
    private fun networkAvailable():Boolean{val cm=activity.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager;val n=cm.activeNetwork?:return false;val c=cm.getNetworkCapabilities(n)?:return false;return c.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)}
    @JavascriptInterface fun setApiBaseUrl(url:String):Boolean{val v=url.trim().trimEnd('/');if(v.isNotBlank()&&!v.startsWith("https://",ignoreCase=true))return false;prefs.edit().putString("api_base",v).apply();return true}
    @JavascriptInterface fun getApiBaseUrl():String=apiBase()
    @JavascriptInterface fun requestPttAudioPermission():Boolean{if(activity.hasRecordAudioPermission())return true;activity.requestRecordAudioPermission();return false}
    @JavascriptInterface fun getPttProofPublicBundle(deviceId:String):String=pttProof.publicBundle(deviceId).toString()
    @JavascriptInterface fun signPttProof(caseId:String,deviceId:String,action:String,nonce:String,timestampMs:Long):String=pttProof.sign(caseId,deviceId,action,nonce,timestampMs).toString()
    @JavascriptInterface fun configurePttAudio(caseId:String,talkgroup:String,deviceId:String,proofSession:String):String=pttAudio.configure(caseId,talkgroup,deviceId,proofSession).toString()
    @JavascriptInterface fun startPttAudio(caseId:String,talkgroup:String,deviceId:String,proofSession:String):String=pttAudio.startTransmit(caseId,talkgroup,deviceId,proofSession).toString()
    @JavascriptInterface fun stopPttAudio():String=pttAudio.stopTransmit().toString()
    fun shutdownPttAudio(){pttAudio.shutdown()}
    @JavascriptInterface fun getDeviceSnapshot():String=activity.deviceSnapshotJson(store.queueDepth())
    @JavascriptInterface fun getBSIEPose():String=activity.nativeBSIEPoseJson()
    @JavascriptInterface fun getBSIEWorldGeometry():String=activity.nativeWorldGeometryJson()
    @JavascriptInterface fun getMobileSdkStatus():String=activity.nativeMobileSdkJson()

    @JavascriptInterface fun openBSIECommissioning():Boolean=activity.openBSIECommissioning()
    @JavascriptInterface fun getNikiRuntimeStatus():String {
        val raw=NikiMobileRuntime.statusJson()
        return runCatching{JSONObject(raw).put("app_authorized",NikiMobileRuntime.validateApp("searchar")).put("binding_match",NikiMobileRuntime.bindingSha256().equals(BuildConfig.NIKI_MOBILE_BINDING_SHA256,true)).put("expected_binding_sha256",BuildConfig.NIKI_MOBILE_BINDING_SHA256).put("aar_sha256",BuildConfig.NIKI_MOBILE_AAR_SHA256).toString()}.getOrElse{raw}
    }
    @JavascriptInterface fun runNikiCycle(queryDigest:String,adamEvidenceDigest:String,bsieSceneDigest:String,meanConfidence:Double,conflictRatio:Double,evidenceDensity:Double,spatialFreshness:Double,cycleSeed:Long):String =
        NikiMobileRuntime.cycle("searchar",queryDigest,adamEvidenceDigest,bsieSceneDigest,meanConfidence,conflictRatio,evidenceDensity,spatialFreshness,cycleSeed)
    @JavascriptInterface fun saveDraft(key:String,payload:String):Boolean{store.saveDraft(key,payload);return true}
    @JavascriptInterface fun loadDraft(key:String):String=store.loadDraft(key)?:"null"
    @JavascriptInterface fun exportJson(nameRaw:String,content:String):String{val safe=nameRaw.replace(Regex("[^A-Za-z0-9._-]"),"_");val dir=File(activity.getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS),"SearchARExports");dir.mkdirs();val f=File(dir,safe);f.writeText(content,Charsets.UTF_8);return JSONObject().put("saved",true).put("path",f.absolutePath).toString()}
    private fun local(method:String,path:String,body:String):String?{
        if(path=="/health")return JSONObject().put("ok",true).put("native_mobile",true).put("app","SearchAR").put("bsie",JSONObject(activity.nativeMobileSdkJson())).put("queue_depth",store.queueDepth()).toString()
        if(path=="/api/sar/mobile/status")return JSONObject().put("native_mobile",true).put("offline_first",true).put("queue_depth",store.queueDepth()).put("bsie",JSONObject(activity.nativeMobileSdkJson())).toString()
        if(path.startsWith("/api/sar/mobile/draft/")&&method=="GET"){val k=path.substringAfterLast('/');return store.loadDraft(k)?:"null"}
        if(path.startsWith("/api/sar/mobile/draft/")&&method=="PUT"){val k=path.substringAfterLast('/');store.saveDraft(k,body);return body}
        return null
    }
    private fun priority(path:String)=when{path.contains("/emergency-link/")||path.contains("/emergency-lookup")->100;path.contains("/security/")||path.contains("/exchange/")->95;path.contains("/field/evidence")||path.contains("/waypoints/")->90;path.contains("/tracks/")->85;path.contains("/assignments")->80;path.contains("/cop/")->70;else->60}
    private fun queuedReply(path:String,method:String,body:String):String{val id=store.enqueue(path,method,body,priority(path));return JSONObject().put("accepted",true).put("queued",true).put("packet_id",id).put("offline",true).put("store_and_forward",true).put("queue_depth",store.queueDepth()).toString()}
    private fun http(method:String,path:String,body:String):String{val conn=(URL(apiBase()+path).openConnection() as HttpURLConnection);conn.requestMethod=method;conn.connectTimeout=5000;conn.readTimeout=10000;conn.setRequestProperty("Content-Type","application/json");if(method!="GET"&&body.isNotBlank()){conn.doOutput=true;conn.outputStream.use{it.write(body.toByteArray(Charsets.UTF_8))}};val code=conn.responseCode;val stream=if(code in 200..299)conn.inputStream else conn.errorStream;val text=stream?.bufferedReader()?.use{it.readText()}?:"{}";if(code !in 200..299)throw IllegalStateException("HTTP $code $text");return text}
    @JavascriptInterface fun request(methodRaw:String,path:String,bodyRaw:String?):String{
        val method=methodRaw.uppercase();val body=bodyRaw?:"{}";local(method,path,body)?.let{return it}
        if(apiBase().isNotBlank()&&networkAvailable()){val result=runCatching{http(method,path,body)};if(result.isSuccess){val raw=result.getOrThrow();if(method=="GET")store.cacheResponse(path,raw);return raw}}
        val liveOnly=path.startsWith("/api/sar/comms/ptt/")||path=="/api/sar/comms/link"
        if(liveOnly)return JSONObject().put("accepted",false).put("offline",true).put("error","live_comms_required").put("path",path).toString()
        if(method in setOf("POST","PUT","PATCH","DELETE")&&path.startsWith("/api/sar/"))return queuedReply(path,method,body)
        return store.cachedResponse(path)?:JSONObject().put("offline",true).put("path",path).put("queue_depth",store.queueDepth()).toString()
    }
    @JavascriptInterface fun flushOutbox():String{
        if(apiBase().isBlank()||!networkAvailable())return JSONObject().put("routed_count",0).put("remaining",store.queueDepth()).toString()
        var sent=0;val q=store.queued();for(i in 0 until q.length()){val x=q.getJSONObject(i);runCatching{http(x.getString("method"),x.getString("path"),x.getString("body"));store.markSent(x.getString("packet_id"));sent++}}
        return JSONObject().put("routed_count",sent).put("remaining",store.queueDepth()).toString()
    }
}
