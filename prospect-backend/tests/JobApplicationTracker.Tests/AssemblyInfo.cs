using Xunit;

// TestCurrentUserService.CurrentUserId is a process-wide static that several
// controller test classes assign before each request. xUnit runs test classes
// in parallel by default, so two classes racing on that static would hand a
// request the wrong user id. Serialising the assembly is the cheapest correct
// fix; every class already spins up its own Testcontainer, so the wall-clock
// cost is small.
[assembly: CollectionBehavior(DisableTestParallelization = true)]
