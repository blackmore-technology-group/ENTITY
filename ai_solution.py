```tla
\begin{module}
  \begin{Constants}
    \const{Subject}, \const{Isser}, \const{Claim}, \const{VerifiedClaim} \in \{\dots\}
  \end{Constants}

  \begin{Variables}
    \var{User} \in \{\langle \var{Subject}, \var{Isser} \rangle \}^?

    \var{Issuer} \in \{\langle \var{Subject}, \var{Isser}, \var{Claim} \rangle \}^?

    \var{Verification} \in \{\langle \var{Subject}, \var{Isser}, \var{VerifiedClaim} \rangle \}^?
  \end{Variables}

  \begin{Invariants}
    \forall v \in \var{Verification}. \langle v.Subject, v.Isser, v.Claim \rangle \in \var{Issuer}

    \forall v \in \var{Verification}. \langle v.Subject, v.Isser \rangle \in \var{User}
  \end{Invariants}
\end{module}
```