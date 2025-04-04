curl -X POST -H "Content-Type: application/json" -d '{
  "query": "query($loanAmount: Float!, $clientInfo: String!) { riskProfile(loanAmount: $loanAmount, clientInfo: $clientInfo) }",
  "variables": {"loanAmount": 15000, "clientInfo": "Infos client"}
}' http://localhost:5001/graphql

curl -X POST -H "Content-Type: application/json" -d '{
  "query": "query($loanAmount: Float!, $clientInfo: String!) { riskProfile(loanAmount: $loanAmount, clientInfo: $clientInfo) }",
  "variables": {"loanAmount": 25000, "clientInfo": "Infos client"}
}' http://localhost:5001/graphqlkuygt