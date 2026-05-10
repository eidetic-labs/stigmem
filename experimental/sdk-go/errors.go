package stigmem

import "fmt"

// StigmemError is returned for non-2xx HTTP responses.
type StigmemError struct {
	StatusCode int
	Detail     string
}

func (e *StigmemError) Error() string {
	return fmt.Sprintf("stigmem: HTTP %d: %s", e.StatusCode, e.Detail)
}

// StigmemAuthError wraps 401/403 responses.
type StigmemAuthError struct{ StigmemError }

// StigmemNotFoundError wraps 404 responses.
type StigmemNotFoundError struct{ StigmemError }

// StigmemConflictError wraps 409 responses.
type StigmemConflictError struct{ StigmemError }

func newHTTPError(code int, detail string) error {
	base := StigmemError{StatusCode: code, Detail: detail}
	switch {
	case code == 401 || code == 403:
		return &StigmemAuthError{base}
	case code == 404:
		return &StigmemNotFoundError{base}
	case code == 409:
		return &StigmemConflictError{base}
	default:
		return &base
	}
}
