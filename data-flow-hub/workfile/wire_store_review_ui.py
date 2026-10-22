from pathlib import Path
p=Path('outputs/V1.8.0/frontend-github/src/BatchLogs.jsx');s=p.read_text(encoding='utf-8')
s="import NewStoreReview from './NewStoreReview';\n"+s
s=s.replace('Check,LoaderCircle','Check,LoaderCircle,Store')
s=s.replace("[configurationJob,setConfigurationJob]=useState(null)","[configurationJob,setConfigurationJob]=useState(null),[storeReviewJob,setStoreReviewJob]=useState(null)")
s=s.replace(' return <div className="space-y-6" data-testid="batch-logs">'," if(storeReviewJob)return <NewStoreReview jobId={storeReviewJob} onBack={()=>{setStoreReviewJob(null);refresh().catch(e=>setError(e.message));}}/>;\n return <div className=\"space-y-6\" data-testid=\"batch-logs\">")
needle="<button disabled={busy||!!pending} className={iconButton+' text-cyan-300'}"
s=s.replace(needle,"{job.status!=='Cancelled Job'&&job.metrics?.newStores?.length>0&&<button className={iconButton+' text-amber-300'} disabled={busy} aria-label=\"Review New Stores\" title=\"Review New Stores\" onClick={()=>setStoreReviewJob(job.id)}><Store size={16}/></button>}"+needle,1)
s=s.replace('New stores are added to Store Table Management when the job is approved.','New stores are added only through Review New Stores → Approve New Stores. Approve Job is separate.')
s=s.replace("{m.newStoresAddedOnApproval!=null&&` Added on approval: ${m.newStoresAddedOnApproval}.`}","{m.newStoresApprovedCount!=null&&` New stores approved: ${m.newStoresApprovedCount}.`}{m.newStoresAddedOnApproval!=null&&` Added by earlier job-approval workflow: ${m.newStoresAddedOnApproval}.`}")
s=s.replace('<AuditMetrics metrics={audit.job.metrics}/>', '<AuditMetrics metrics={audit.job.metrics}/>{audit.job.metrics?.newStores?.length>0&&<button className={button+\' mb-4 text-amber-300\'} onClick={()=>{setStoreReviewJob(audit.job.id);setAudit(null);}}>Review New Stores</button>}')
p.write_text(s,encoding='utf-8')
print('New Store review UI ready')
