-- Step: production safety net.
-- The frontend deletes a document when the user leaves, but a crashed browser or a
-- dropped connection can skip that. This hourly job removes anything older than 2 hours.
-- Run once in Supabase: SQL Editor -> New query -> paste -> Run. Safe to re-run.

create index if not exists chunks_created_at_idx on chunks (created_at);

create extension if not exists pg_cron;

-- Remove an older copy of the job if this script is run again.
select cron.unschedule(jobid) from cron.job where jobname = 'delete-stale-chunks';

select cron.schedule(
  'delete-stale-chunks',
  '7 * * * *',  -- every hour at :07
  $$ delete from public.chunks where created_at < now() - interval '2 hours' $$
);

-- Check it:   select jobname, schedule, active from cron.job;
-- History:    select status, start_time from cron.job_run_details order by start_time desc limit 5;
