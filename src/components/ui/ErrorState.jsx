export default function ErrorState({ message, onRetry }) { return <div className="alert error-alert"><span>{message}</span>{onRetry && <button onClick={onRetry}>Retry</button>}</div> }
